"""
gpt4o_analyzer.py — Activity Analysis using OpenAI GPT-4o Vision
==================================================================
Analyzes detected unknown faces and their activities using GPT-4o Vision
to determine if suspicious behavior is detected.

Architecture:
  • Captures 1 frame every ~2 seconds when an unknown face is present
  • Sends the frame to GPT-4o Vision for analysis
  • Returns suspicion score (0.0 - 1.0) and reasoning
  • Caches results to avoid duplicate API calls
  • Threaded to avoid blocking video processing

Requirements:
  pip install openai pillow
"""

import os
import json
import time
import base64
import logging
import asyncio
from typing import Dict, List, Optional
from collections import defaultdict

try:
    from openai import AsyncOpenAI
    OPENAI_IMPORT_ERROR = None
except ImportError as e:
    AsyncOpenAI = None
    OPENAI_IMPORT_ERROR = e

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [GPT4O] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GPT4oActivityAnalyzer:
    """
    Analyzes face frames using OpenAI GPT-4o Vision for suspicious behavior detection.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        if AsyncOpenAI is None:
            raise ImportError(
                f"openai package is not installed: {OPENAI_IMPORT_ERROR}\n"
                "Fix: pip install openai pillow"
            )

        self.api_key = api_key
        self.model_name = model
        self.client = AsyncOpenAI(api_key=api_key)

        self.analysis_cache: Dict[str, Dict] = {}
        self.cache_ttl = 60           # 1-minute TTL — short because we send a frame every 2 s
        self.activity_history: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = 50

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

        logger.info(f"GPT-4o Activity Analyzer initialized — model: {model}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _encode_frame(self, frame_bytes: bytes) -> str:
        """Return base64-encoded JPEG string for the OpenAI Vision API."""
        return base64.b64encode(frame_bytes).decode("utf-8")

    def _get_cache_key(self, face_id: str, timestamp: float) -> str:
        bucket = int(timestamp / 2)   # 2-second windows match the send rate
        return f"{face_id}:{bucket}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.analysis_cache:
            return False
        age = time.time() - self.analysis_cache[cache_key].get("timestamp", 0)
        return age < self.cache_ttl

    # ── Single-frame analysis (primary path) ──────────────────────────────────

    async def analyze_activity_async(
        self,
        frame_bytes: bytes,
        face_id: str,
        person_name: str,
        coordinates: Dict,
        timestamp: float,
    ) -> Dict:
        cache_key = self._get_cache_key(face_id, timestamp)
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {face_id}")
            return self.analysis_cache[cache_key]

        try:
            b64 = self._encode_frame(frame_bytes)
            prompt = self._build_prompt(person_name, coordinates)
            raw_text = await self._call_api(b64, prompt)
            analysis = self._parse_response(raw_text, face_id, timestamp)
            self.analysis_cache[cache_key] = analysis
            self._add_to_history(face_id, analysis)
            logger.info(
                f"Analysis for {person_name} ({face_id}): "
                f"score={analysis['suspicion_score']:.2f} "
                f"suspicious={analysis['is_suspicious']}"
            )
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing activity: {e}")
            return self._fallback_analysis(face_id, timestamp)

    # ── Video-chunk entry point (called from multiple_tracking.py) ────────────

    async def analyze_video_chunk_async(
        self,
        frame_bytes_list: List[bytes],
        face_id: str,
        person_name: str,
        coordinates: Dict,
        timestamp: float,
    ) -> Dict:
        """
        Receives a list of frames (typically 1 with the 2-second buffer).
        Uses only the most recent frame for the GPT-4o call.
        """
        cache_key = self._get_cache_key(face_id, timestamp)
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {face_id}")
            return self.analysis_cache[cache_key]

        if not frame_bytes_list:
            return self._fallback_analysis(face_id, timestamp)

        # Use the last (most recent) frame
        frame_bytes = frame_bytes_list[-1]

        try:
            b64 = self._encode_frame(frame_bytes)
            prompt = self._build_prompt(person_name, coordinates)
            raw_text = await self._call_api(b64, prompt)
            analysis = self._parse_response(raw_text, face_id, timestamp)
            self.analysis_cache[cache_key] = analysis
            self._add_to_history(face_id, analysis)
            logger.info(
                f"GPT-4o frame analysis for {person_name} ({face_id}): "
                f"score={analysis['suspicion_score']:.2f} "
                f"risk={analysis.get('risk_level', '?')}"
            )
            return analysis
        except Exception as e:
            logger.error(f"Error in video_chunk analysis for {face_id}: {e}")
            return self._fallback_analysis(face_id, timestamp)

    # ── Prompt ────────────────────────────────────────────────────────────────

    def _build_prompt(self, person_name: str, coordinates: Dict) -> str:
        return (
            "You are a security system AI. Analyze this surveillance camera frame for suspicious activity.\n\n"
            f"Context:\n"
            f"- Person Status: {person_name}\n"
            f"- Location in frame: ({coordinates.get('x', '?')}, {coordinates.get('y', '?')})\n"
            f"- Bounding box: {coordinates.get('w', '?')}x{coordinates.get('h', '?')} pixels\n\n"
            "Please analyze and provide:\n"
            "1. activity: Describe what the person is doing.\n"
            "2. suspicion_score: Float 0.0 (not suspicious) to 1.0 (highly suspicious).\n"
            f"3. patterns: List any from: {', '.join(self.suspicious_patterns)}\n"
            "4. behavior: Describe posture, hand placement, and overall demeanor.\n"
            "5. risk_level: LOW, MEDIUM, or HIGH.\n"
            "6. reasoning: Brief explanation of your assessment.\n"
            "7. confidence: Float 0.0-1.0 for your confidence.\n\n"
            "Respond ONLY with valid JSON using exactly these keys: "
            "activity, suspicion_score, patterns, behavior, risk_level, reasoning, confidence"
        )

    # ── API Call ──────────────────────────────────────────────────────────────

    async def _call_api(self, b64_image: str, prompt: str) -> str:
        """
        Send a single base64 frame to GPT-4o Vision.
        Retries up to 3 times with exponential back-off on rate-limit errors.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    max_tokens=512,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}",
                                        "detail": "low",   # cheaper + faster
                                    },
                                },
                            ],
                        }
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "quota" in err_str or "rate" in err_str
                if is_rate_limit and attempt < max_retries - 1:
                    wait = 2 ** attempt * 15   # 15 s, 30 s
                    logger.warning(
                        f"OpenAI rate limit (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

    # ── Response Parsing ──────────────────────────────────────────────────────

    def _parse_response(self, text: str, face_id: str, timestamp: float) -> Dict:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                cleaned = parts[1] if len(parts) > 1 else cleaned
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            data = json.loads(cleaned)

            suspicion_score = float(data.get("suspicion_score", 0.0))
            risk_level = str(data.get("risk_level", "UNKNOWN")).upper()

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
            logger.warning(f"Error parsing GPT-4o response ({e}), using fallback")
            return self._fallback_analysis(face_id, timestamp)

    def _fallback_analysis(self, face_id: str, timestamp: float) -> Dict:
        return {
            "suspicion_score": 0.0,
            "is_suspicious": False,
            "activities": ["Unable to analyze"],
            "behavior": "API unavailable",
            "patterns_detected": [],
            "risk_level": "UNKNOWN",
            "reasoning": "GPT-4o API unavailable — returning neutral analysis",
            "confidence": 0.0,
            "timestamp": timestamp,
            "face_id": face_id,
        }

    # ── History & Summaries ───────────────────────────────────────────────────

    def _add_to_history(self, face_id: str, analysis: Dict) -> None:
        self.activity_history[face_id].append(analysis)
        if len(self.activity_history[face_id]) > self.max_history:
            self.activity_history[face_id] = self.activity_history[face_id][-self.max_history:]

    def get_activity_summary(self, face_id: str) -> Dict:
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
        avg = sum(scores) / len(scores)
        mx = max(scores)
        if len(history) >= 3:
            recent = sum(scores[-3:]) / 3
            older = sum(scores[:-3]) / (len(scores) - 3) if len(scores) > 3 else 0.0
            trend = "INCREASING" if recent > older + 0.1 else "DECREASING" if recent < older - 0.1 else "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"
        return {
            "face_id": face_id,
            "total_detections": len(history),
            "suspicious_count": suspicious_count,
            "avg_suspicion": round(avg, 3),
            "max_suspicion": round(mx, 3),
            "risk_trend": trend,
            "latest_analysis": history[-1],
        }

    def get_suspicious_activities_log(self, min_suspicion: float = 0.6) -> List[Dict]:
        suspicious = []
        for face_id, history in self.activity_history.items():
            for analysis in history:
                if analysis.get("suspicion_score", 0.0) >= min_suspicion:
                    suspicious.append({"face_id": face_id, **analysis})
        return sorted(suspicious, key=lambda x: x["timestamp"], reverse=True)

    def clear_cache(self) -> None:
        self.analysis_cache.clear()
        logger.info("Analysis cache cleared")

    def close(self) -> None:
        """No-op for API compatibility."""
        pass


# ── Singleton ──────────────────────────────────────────────────────────────────
_analyzer_instance: Optional[GPT4oActivityAnalyzer] = None


def get_analyzer(api_key: str, model: str = "gpt-4o") -> GPT4oActivityAnalyzer:
    """Get or create the singleton GPT-4o analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = GPT4oActivityAnalyzer(api_key, model)
    return _analyzer_instance
