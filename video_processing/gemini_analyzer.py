"""
gemini_analyzer.py — Activity Analysis using Google Gemini API
==================================================================
Analyzes detected unknown faces and their activities using Gemini Vision
to determine if suspicious behavior is detected.

Architecture:
  • Captures live frames when unknown faces are detected
  • Sends frame + context to Gemini for analysis
  • Returns suspicion score (0.0 - 1.0) and reasoning
  • Caches results to avoid duplicate API calls
  • Threaded to avoid blocking video processing

Requirements:
  pip install google-generativeai pillow
"""

import os
import io
import json
import time
import base64
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import asyncio

try:
    import google.generativeai as genai
    import PIL.Image
    GEMINI_IMPORT_ERROR = None
except ImportError as e:
    genai = None
    GEMINI_IMPORT_ERROR = e

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [GEMINI] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GeminiActivityAnalyzer:
    """
    Analyzes face frames and activities using Google Gemini API for suspicious behavior detection.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """
        Initialize Gemini analyzer.

        Args:
            api_key: Google Gemini API key
            model: Gemini model to use (gemini-2.0-flash, gemini-1.5-flash, etc.)
        """
        if genai is None:
            raise ImportError(
                f"google-generativeai is not installed: {GEMINI_IMPORT_ERROR}\n"
                "Fix: pip install google-generativeai pillow"
            )

        self.api_key = api_key
        self.model_name = model

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

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
            "erratic movement",
        ]

        logger.info(f"Gemini Activity Analyzer initialized with model: {model}")

    # ── Frame Helpers ──────────────────────────────────────────────────────────

    def _decode_frame_to_pil(self, frame_bytes: bytes) -> "PIL.Image.Image":
        """Decode JPEG bytes to a PIL Image for Gemini."""
        return PIL.Image.open(io.BytesIO(frame_bytes))

    def _get_cache_key(self, face_id: str, timestamp: float) -> str:
        """Generate cache key; buckets timestamp in 30-second windows."""
        bucket = int(timestamp / 30)
        return f"{face_id}:{bucket}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Return True if cached analysis is still within TTL."""
        if cache_key not in self.analysis_cache:
            return False
        age = time.time() - self.analysis_cache[cache_key].get("timestamp", 0)
        return age < self.cache_ttl

    # ── Public Analysis Entry Point ────────────────────────────────────────────

    async def analyze_activity_async(
        self,
        frame_bytes: bytes,
        face_id: str,
        person_name: str,
        coordinates: Dict,
        timestamp: float,
    ) -> Dict:
        """
        Asynchronously analyze a frame for suspicious activity.

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
                'behavior': str,
                'patterns_detected': [list of suspicious patterns],
                'risk_level': str,
                'reasoning': str,
                'confidence': float,
                'timestamp': float,
                'face_id': str
            }
        """
        cache_key = self._get_cache_key(face_id, timestamp)
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {face_id}")
            return self.analysis_cache[cache_key]

        try:
            pil_image = self._decode_frame_to_pil(frame_bytes)
            prompt = self._build_analysis_prompt(person_name, coordinates)

            raw_text = await self._call_gemini_api(pil_image, prompt)

            analysis = self._process_response_text(raw_text, face_id, timestamp)
            self.analysis_cache[cache_key] = analysis
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

    # ── Video Chunk Analysis ───────────────────────────────────────────────────

    async def analyze_video_chunk_async(
        self,
        frame_bytes_list: List[bytes],
        face_id: str,
        person_name: str,
        coordinates: Dict,
        timestamp: float,
    ) -> Dict:
        """
        Analyze a sequence of frames (10-second buffer) for suspicious activity.
        Sends all sampled frames in one API call to reduce request rate.

        Args:
            frame_bytes_list: List of JPEG frame bytes sampled over ~10 seconds
            face_id: Unique face identifier
            person_name: Person name ('UNKNOWN' for suspicious check)
            coordinates: Face bounding box coordinates
            timestamp: Analysis timestamp

        Returns:
            Same dict shape as analyze_activity_async
        """
        cache_key = self._get_cache_key(face_id, timestamp)
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {face_id}")
            return self.analysis_cache[cache_key]

        try:
            pil_images = [self._decode_frame_to_pil(fb) for fb in frame_bytes_list]
            prompt = self._build_video_chunk_prompt(person_name, coordinates, len(pil_images))

            # Send prompt + all frames as a single Gemini request
            content = [prompt] + pil_images
            raw_text = await asyncio.to_thread(
                self.model.generate_content,
                content,
            )
            analysis = self._process_response_text(raw_text.text, face_id, timestamp)
            self.analysis_cache[cache_key] = analysis
            self._add_to_history(face_id, analysis)

            logger.info(
                f"Video-chunk analysis for {person_name} (ID: {face_id}): "
                f"{len(pil_images)} frames — "
                f"Suspicion={analysis['suspicion_score']:.2f}, "
                f"Risk={analysis.get('risk_level', '?')}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing video chunk for {face_id}: {e}")
            return self._fallback_analysis(face_id, timestamp)

    # ── Prompt Builder ─────────────────────────────────────────────────────────

    def _build_video_chunk_prompt(self, person_name: str, coordinates: Dict, num_frames: int) -> str:
        """Build temporal prompt for multi-frame (video chunk) analysis."""
        return (
            f"Analyze these {num_frames} surveillance camera frames captured over ~10 seconds "
            "for suspicious activity.\n\n"
            f"Context:\n"
            f"- Person Status: {person_name}\n"
            f"- Location in frame: ({coordinates.get('x', '?')}, {coordinates.get('y', '?')})\n"
            f"- Bounding box: {coordinates.get('w', '?')}x{coordinates.get('h', '?')} pixels\n"
            f"- Frames span: ~10 seconds of real-time footage\n\n"
            "These frames form a TEMPORAL SEQUENCE. Look for movement patterns and behavioral "
            "changes across the sequence, not just individual poses.\n\n"
            "Please analyze and provide:\n"
            "1. Activity: Describe what activities the person performs across these frames.\n"
            "2. Suspicion Score: Rate suspicion from 0.0 (not suspicious) to 1.0 (highly suspicious).\n"
            f"3. Patterns: List any patterns from: {', '.join(self.suspicious_patterns)}\n"
            "4. Behavior: Analyze posture, movement trajectory, hand placement, and temporal behavior.\n"
            "5. Risk Level: Classify as LOW, MEDIUM, or HIGH.\n"
            "6. Reasoning: Include temporal observations (e.g. 'moved towards X', 'lingered at Y').\n\n"
            "Respond ONLY with valid JSON using these keys: "
            "activity, suspicion_score, patterns, behavior, risk_level, reasoning, confidence"
        )

    def _build_analysis_prompt(self, person_name: str, coordinates: Dict) -> str:
        """Build single-frame prompt for Gemini analysis (legacy fallback)."""
        return (
            "Analyze this surveillance camera frame for suspicious activity.\n\n"
            f"Context:\n"
            f"- Person Status: {person_name}\n"
            f"- Location in frame: ({coordinates.get('x', '?')}, {coordinates.get('y', '?')})\n"
            f"- Bounding box: {coordinates.get('w', '?')}x{coordinates.get('h', '?')} pixels\n\n"
            "Please analyze and provide:\n"
            "1. Activity: Describe what activities the person is performing.\n"
            "2. Suspicion Score: Rate suspicion from 0.0 (not suspicious) to 1.0 (highly suspicious).\n"
            f"3. Patterns: List any patterns from: {', '.join(self.suspicious_patterns)}\n"
            "4. Behavior: Analyze posture, hand placement, eye movement, and overall behavior.\n"
            "5. Risk Level: Classify as LOW, MEDIUM, or HIGH.\n"
            "6. Reasoning: Provide detailed reasoning for your assessment.\n\n"
            "Respond ONLY with valid JSON using these keys: "
            "activity, suspicion_score, patterns, behavior, risk_level, reasoning, confidence"
        )

    # ── Gemini API Call ────────────────────────────────────────────────────────

    async def _call_gemini_api(self, image: "PIL.Image.Image", prompt: str) -> str:
        """
        Send image + prompt to Gemini and return the raw text response.
        Runs the blocking SDK call in a thread so the event loop isn't blocked.
        """
        response = await asyncio.to_thread(
            self.model.generate_content,
            [prompt, image],
        )
        return response.text

    # ── Response Parsing ───────────────────────────────────────────────────────

    def _process_response_text(self, text: str, face_id: str, timestamp: float) -> Dict:
        """Parse Gemini's text response into a structured analysis dict."""
        try:
            # Strip markdown code fences if Gemini wraps the JSON
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            suspicion_score = float(data.get("suspicion_score", 0.0))
            risk_level = str(data.get("risk_level", "UNKNOWN")).upper()

            # Derive suspicion_score from risk_level when absent
            if suspicion_score == 0.0 and risk_level != "UNKNOWN":
                suspicion_score = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.9}.get(risk_level, 0.5)

            activity = data.get("activity", "")
            activities = (
                [a.strip() for a in activity.split(",")]
                if isinstance(activity, str)
                else [str(activity)]
            )

            return {
                "suspicion_score": min(1.0, max(0.0, suspicion_score)),
                "is_suspicious": suspicion_score > 0.6,
                "activities": activities,
                "behavior": data.get("behavior", "No behavior analysis available"),
                "patterns_detected": data.get("patterns", []),
                "risk_level": risk_level,
                "reasoning": data.get("reasoning", "Analysis complete"),
                "confidence": float(data.get("confidence", 0.75)),
                "timestamp": timestamp,
                "face_id": face_id,
            }

        except Exception as e:
            logger.warning(f"Error parsing Gemini response, using fallback: {e}")
            return self._fallback_analysis(face_id, timestamp)

    # ── Fallback ───────────────────────────────────────────────────────────────

    def _fallback_analysis(self, face_id: str, timestamp: float) -> Dict:
        """Return a neutral analysis when the API call or parsing fails."""
        return {
            "suspicion_score": 0.0,
            "is_suspicious": False,
            "activities": ["Unable to analyze"],
            "behavior": "API unavailable",
            "patterns_detected": [],
            "risk_level": "UNKNOWN",
            "reasoning": "Gemini API unavailable — returning neutral analysis",
            "confidence": 0.0,
            "timestamp": timestamp,
            "face_id": face_id,
        }

    # ── History & Summaries ────────────────────────────────────────────────────

    def _add_to_history(self, face_id: str, analysis: Dict) -> None:
        """Append analysis to rolling activity history."""
        self.activity_history[face_id].append(analysis)
        if len(self.activity_history[face_id]) > self.max_history:
            self.activity_history[face_id] = self.activity_history[face_id][-self.max_history:]

    def get_activity_summary(self, face_id: str) -> Dict:
        """Return aggregated activity summary for a face."""
        history = self.activity_history.get(face_id, [])
        if not history:
            return {
                "face_id": face_id,
                "total_detections": 0,
                "suspicious_count": 0,
                "avg_suspicion": 0.0,
                "max_suspicion": 0.0,
                "risk_trend": "STABLE",
            }

        suspicious_count = sum(1 for a in history if a.get("is_suspicious", False))
        scores = [a.get("suspicion_score", 0.0) for a in history]
        avg_suspicion = sum(scores) / len(scores)
        max_suspicion = max(scores)

        if len(history) >= 3:
            recent_avg = sum(scores[-3:]) / 3
            older_avg = sum(scores[:-3]) / (len(scores) - 3) if len(scores) > 3 else 0.0
            if recent_avg > older_avg + 0.1:
                trend = "INCREASING"
            elif recent_avg < older_avg - 0.1:
                trend = "DECREASING"
            else:
                trend = "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"

        return {
            "face_id": face_id,
            "total_detections": len(history),
            "suspicious_count": suspicious_count,
            "avg_suspicion": round(avg_suspicion, 3),
            "max_suspicion": round(max_suspicion, 3),
            "risk_trend": trend,
            "latest_analysis": history[-1],
        }

    def get_suspicious_activities_log(self, min_suspicion: float = 0.6) -> List[Dict]:
        """Return time-sorted list of analyses above the suspicion threshold."""
        suspicious = []
        for face_id, history in self.activity_history.items():
            for analysis in history:
                if analysis.get("suspicion_score", 0.0) >= min_suspicion:
                    suspicious.append({"face_id": face_id, **analysis})
        return sorted(suspicious, key=lambda x: x["timestamp"], reverse=True)

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")

    def close(self) -> None:
        """No-op kept for API compatibility with the old HTTP-client-based analyzer."""
        pass


# ── Singleton ──────────────────────────────────────────────────────────────────
_analyzer_instance: Optional[GeminiActivityAnalyzer] = None


def get_analyzer(api_key: str, model: str = "gemini-2.0-flash") -> GeminiActivityAnalyzer:
    """Get or create the singleton GeminiActivityAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GeminiActivityAnalyzer(api_key, model)
    return _analyzer_instance
