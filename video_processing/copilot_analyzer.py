"""
copilot_analyzer.py — Activity Analysis using Claude Copilot API
==================================================================
Analyzes detected unknown faces and their activities using Claude Vision
to determine if suspicious behavior is detected.

Architecture:
  • Captures live frames when unknown faces are detected
  • Sends frame + context to Claude Copilot for analysis
  • Returns suspicion score (0.0 - 1.0) and reasoning
  • Caches results to avoid duplicate API calls
  • Threaded to avoid blocking video processing
"""

import os
import json
import time
import base64
import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import httpx
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [COPILOT] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CopilotActivityAnalyzer:
    """
    Analyzes face frames and activities using Claude API for suspicious behavior detection.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4-vision"):
        """
        Initialize Copilot analyzer.
        
        Args:
            api_key: Claude API key
            model: Model to use (gpt-4-vision, gpt-4-turbo, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"  # Will use Claude endpoint
        self.client = httpx.Client(timeout=30.0)
        
        # Cache to avoid analyzing same face multiple times
        self.analysis_cache: Dict[str, Dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self.activity_history: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = 50
        
        # Known suspicious activity patterns
        self.suspicious_patterns = [
            "loitering",
            "weapon carrying",
            "vandalism",
            "theft",
            "aggressive behavior",
            "unauthorized access",
            "trespassing",
            "suspicious tools",
            "covering face",
            "erratic movement"
        ]
        
        logger.info(f"Copilot Activity Analyzer initialized with model: {model}")
    
    def _encode_frame_to_base64(self, frame_bytes: bytes) -> str:
        """Encode frame bytes to base64 for API transmission."""
        return base64.b64encode(frame_bytes).decode('utf-8')
    
    def _get_cache_key(self, face_id: str, timestamp: float) -> str:
        """Generate cache key for frame analysis."""
        # Round timestamp to nearest 30 seconds to batch similar frames
        bucket = int(timestamp / 30)
        return f"{face_id}:{bucket}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached analysis is still valid."""
        if cache_key not in self.analysis_cache:
            return False
        
        cached = self.analysis_cache[cache_key]
        age = time.time() - cached.get('timestamp', 0)
        return age < self.cache_ttl
    
    async def analyze_activity_async(
        self,
        frame_bytes: bytes,
        face_id: str,
        person_name: str,
        coordinates: Dict,
        timestamp: float
    ) -> Dict:
        """
        Asynchronously analyze frame for suspicious activity.
        
        Args:
            frame_bytes: JPEG frame bytes
            face_id: Unique face identifier
            person_name: Person name (should be "UNKNOWN" for suspicious check)
            coordinates: Face bounding box coordinates
            timestamp: Frame timestamp
            
        Returns:
            {
                'suspicion_score': float (0.0-1.0),
                'is_suspicious': bool,
                'activities': [list of detected activities],
                'reasoning': str,
                'patterns_detected': [list of suspicious patterns],
                'confidence': float,
                'timestamp': float,
                'face_id': str
            }
        """
        
        # Check cache first
        cache_key = self._get_cache_key(face_id, timestamp)
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {face_id}")
            return self.analysis_cache[cache_key]
        
        try:
            # Encode frame
            frame_b64 = self._encode_frame_to_base64(frame_bytes)
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(person_name, coordinates)
            
            # Call Copilot API
            result = await self._call_copilot_api(frame_b64, prompt)
            
            # Process and cache result
            analysis = self._process_api_response(result, face_id, timestamp)
            self.analysis_cache[cache_key] = analysis
            
            # Store in history
            self._add_to_history(face_id, analysis)
            
            logger.info(
                f"Activity analysis for {person_name} (ID: {face_id}): "
                f"Suspicion={analysis['suspicion_score']:.2f}, "
                f"Is_Suspicious={analysis['is_suspicious']}"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing activity: {e}")
            return self._fallback_analysis(face_id, timestamp)
    
    def _build_analysis_prompt(self, person_name: str, coordinates: Dict) -> str:
        """Build detailed prompt for Copilot analysis."""
        return f"""Analyze this surveillance camera frame for suspicious activity.

Context:
- Person Status: {person_name}
- Location: {coordinates.get('x', 'unknown')}, {coordinates.get('y', 'unknown')}
- Frame Size: {coordinates.get('w', 'unknown')}x{coordinates.get('h', 'unknown')} pixels

Please analyze and provide:
1. Activity Assessment: Describe what activities the person is performing
2. Suspicion Score: Rate suspicion level from 0.0 (not suspicious) to 1.0 (highly suspicious)
3. Detected Patterns: List any suspicious patterns from: {', '.join(self.suspicious_patterns)}
4. Behavioral Analysis: Analyze posture, hand placement, eye movement, and overall behavior
5. Risk Level: Classify as LOW, MEDIUM, or HIGH risk
6. Reasoning: Provide detailed reasoning for your assessment

Format your response as JSON with keys: activity, suspicion_score, patterns, behavior, risk_level, reasoning"""
    
    async def _call_copilot_api(self, frame_b64: str, prompt: str) -> Dict:
        """Call Claude API for image analysis."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{frame_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.3  # Lower temp for more consistent results
        }
        
        try:
            response = await asyncio.to_thread(
                self.client.post,
                self.api_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Copilot API call failed: {e}")
            raise
    
    def _process_api_response(self, api_response: Dict, face_id: str, timestamp: float) -> Dict:
        """Process and extract structured data from API response."""
        try:
            # Parse the response (Claude returns in choices[0].message.content)
            content = api_response.get('choices', [{}])[0].get('message', {}).get('content', '{}')
            
            # Try to extract JSON from response
            data = json.loads(content) if isinstance(content, str) else content
            
            suspicion_score = float(data.get('suspicion_score', 0.0))
            risk_level = data.get('risk_level', 'UNKNOWN').upper()
            
            # Normalize risk level to suspicion score if not provided
            if suspicion_score == 0.0:
                risk_mapping = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.9}
                suspicion_score = risk_mapping.get(risk_level, 0.5)
            
            return {
                'suspicion_score': min(1.0, max(0.0, suspicion_score)),
                'is_suspicious': suspicion_score > 0.6,
                'activities': data.get('activity', '').split(',') if isinstance(data.get('activity'), str) else [data.get('activity', '')],
                'behavior': data.get('behavior', 'No behavior analysis available'),
                'patterns_detected': data.get('patterns', []),
                'risk_level': risk_level,
                'reasoning': data.get('reasoning', 'Analysis complete'),
                'confidence': float(data.get('confidence', 0.75)),
                'timestamp': timestamp,
                'face_id': face_id
            }
        except Exception as e:
            logger.warning(f"Error parsing API response, using fallback: {e}")
            return self._fallback_analysis(face_id, timestamp)
    
    def _fallback_analysis(self, face_id: str, timestamp: float) -> Dict:
        """Return fallback analysis when API fails."""
        return {
            'suspicion_score': 0.0,
            'is_suspicious': False,
            'activities': ['Unable to analyze'],
            'behavior': 'API unavailable',
            'patterns_detected': [],
            'risk_level': 'UNKNOWN',
            'reasoning': 'Copilot API unavailable - returning neutral analysis',
            'confidence': 0.0,
            'timestamp': timestamp,
            'face_id': face_id
        }
    
    def _add_to_history(self, face_id: str, analysis: Dict) -> None:
        """Add analysis to activity history."""
        self.activity_history[face_id].append(analysis)
        # Keep only recent history
        if len(self.activity_history[face_id]) > self.max_history:
            self.activity_history[face_id] = self.activity_history[face_id][-self.max_history:]
    
    def get_activity_summary(self, face_id: str) -> Dict:
        """Get aggregated activity summary for a face."""
        history = self.activity_history.get(face_id, [])
        if not history:
            return {
                'face_id': face_id,
                'total_detections': 0,
                'suspicious_count': 0,
                'avg_suspicion': 0.0,
                'max_suspicion': 0.0,
                'risk_trend': 'STABLE'
            }
        
        suspicious_count = sum(1 for a in history if a.get('is_suspicious', False))
        suspicion_scores = [a.get('suspicion_score', 0.0) for a in history]
        avg_suspicion = sum(suspicion_scores) / len(suspicion_scores) if suspicion_scores else 0.0
        max_suspicion = max(suspicion_scores) if suspicion_scores else 0.0
        
        # Determine trend
        if len(history) >= 3:
            recent_avg = sum(suspicion_scores[-3:]) / 3
            older_avg = sum(suspicion_scores[:-3]) / (len(suspicion_scores) - 3) if len(suspicion_scores) > 3 else 0.0
            if recent_avg > older_avg + 0.1:
                trend = 'INCREASING'
            elif recent_avg < older_avg - 0.1:
                trend = 'DECREASING'
            else:
                trend = 'STABLE'
        else:
            trend = 'INSUFFICIENT_DATA'
        
        return {
            'face_id': face_id,
            'total_detections': len(history),
            'suspicious_count': suspicious_count,
            'avg_suspicion': round(avg_suspicion, 3),
            'max_suspicion': round(max_suspicion, 3),
            'risk_trend': trend,
            'latest_analysis': history[-1] if history else None
        }
    
    def get_suspicious_activities_log(self, min_suspicion: float = 0.6) -> List[Dict]:
        """Get log of all suspicious activities detected."""
        suspicious = []
        for face_id, history in self.activity_history.items():
            for analysis in history:
                if analysis.get('suspicion_score', 0.0) >= min_suspicion:
                    suspicious.append({
                        'face_id': face_id,
                        **analysis
                    })
        return sorted(suspicious, key=lambda x: x['timestamp'], reverse=True)
    
    def clear_cache(self) -> None:
        """Clear analysis cache."""
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")
    
    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()


# Singleton instance
_analyzer_instance: Optional[CopilotActivityAnalyzer] = None

def get_analyzer(api_key: str, model: str = "gpt-4-vision") -> CopilotActivityAnalyzer:
    """Get or create analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CopilotActivityAnalyzer(api_key, model)
    return _analyzer_instance
