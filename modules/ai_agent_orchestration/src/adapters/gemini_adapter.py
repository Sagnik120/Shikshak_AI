import os
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from modules.ai_agent_orchestration.src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

# A full teaching segment (up to ~600 spoken words plus notes and a visual spec)
# needs real headroom, and a long JSON reply needs longer than a chat turn.
MAX_OUTPUT_TOKENS = 8192
REQUEST_TIMEOUT_SEC = 90.0


class SmartMockLLMAdapter(LLMAdapter):
    """
    Deterministic smart fallback LLM adapter that inspects message context
    and returns valid Contract-compliant JSON payloads for offline and testing runs.
    """

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        system_content = ""
        user_content = ""
        for m in messages:
            if m.get("role") == "system":
                system_content += " " + m.get("content", "")
            else:
                user_content += " " + m.get("content", "")

        sys_lower = system_content.lower()
        full_lower = (system_content + " " + user_content).lower()

        # 1. Questioner Agent -> InteractionEvent (Contract §8)
        if (
            "evaluating student understanding" in sys_lower
            or "interactive question" in sys_lower
            or "interactionevent" in full_lower
        ):
            return json.dumps({
                "node_id": "node_active",
                "question_text": "Which principle describes the conservation of energy in an isolated system?",
                "type": "mcq",
                "options": [
                    "First Law of Thermodynamics",
                    "Second Law of Thermodynamics",
                    "Newton's Third Law",
                    "Ohm's Law"
                ],
                "expected_concept": "First Law of Thermodynamics"
            })

        # 2. Assessment Agent -> AssessmentReport (Contract §12)
        if (
            "assessment evaluator" in sys_lower
            or "assessmentreport" in full_lower
            or "score_pct" in sys_lower
        ):
            return json.dumps({
                "lesson_id": "lesson_auto_generated",
                "score_pct": 95.0,
                "strong_areas": ["Foundational Principles", "Core Mechanics"],
                "weak_areas": [],
                "recommended_next": ["Advanced Problem Solving"],
                "narrative_feedback": "Outstanding progress! You demonstrated thorough understanding across all lesson checkpoints."
            })

        # 3. Explainer Agent -> TeachingSegment (Contract §6)
        if (
            "explaining a specific lesson concept" in sys_lower
            or "teachingsegment" in full_lower
            or ("teaching segment" in sys_lower and "question" not in sys_lower)
        ):
            cue = "emphasis" if "previous_feedback" in full_lower else "neutral"
            return json.dumps({
                "node_id": "node_active",
                "script_text": "Welcome to today's lesson on foundational mechanics. Newton's First Law states that an object will remain at rest or keep moving at a constant velocity unless an unbalanced external force acts upon it. Imagine a spacecraft drifting in deep space — with no friction or gravity, it will coast forward indefinitely without using any fuel. This natural tendency of all matter to resist changes in its state of motion is what we call inertia.",
                "language": "en",
                "visual_spec": {
                    "type": "diagram",
                    "content": "Balanced Forces vs. Unbalanced Net Force: Inertia Vector Map"
                },
                "avatar_cue": cue
            })

        # 4. Planner Agent -> LessonPlan (Contract §5)
        if (
            "lesson planner" in sys_lower
            or "planner" in sys_lower
            or "lessonplan" in full_lower
            or "lesson plan" in sys_lower
            or "curriculum" in full_lower
        ):
            return json.dumps({
                "lesson_id": "lesson_auto_generated",
                "source": "document" if "document_id" in full_lower else "topic",
                "constraints": {
                    "level": "beginner",
                    "language": "en",
                    "time_budget_min": 15
                },
                "nodes": [
                    {
                        "node_id": "node_1_intro",
                        "concept": "Foundational Principles",
                        "depth": "intro",
                        "est_minutes": 5,
                        "visual_type": "diagram",
                        "checkpoint_question": False
                    },
                    {
                        "node_id": "node_2_core",
                        "concept": "Core Mechanics and Equations",
                        "depth": "core",
                        "est_minutes": 10,
                        "visual_type": "equation",
                        "checkpoint_question": True
                    }
                ]
            })

        # 5. ML Core Evaluation / Misconceptions
        if "misconception" in full_lower:
            return json.dumps({
                "misconception_tag": "gravity-mass-dependence"
            })
            
        if "grading a student" in full_lower or "evaluation" in full_lower:
            return json.dumps({
                "correct": True,
                "confidence": 1.0,
                "partial_credit": 0.0,
                "feedback_text": "Excellent explanation! Your reasoning matches the expected scientific concept."
            })

        # Default fallback
        return json.dumps({"status": "ok", "message": "SmartMock completed"})


def _load_env():
    """Silently populate os.environ from root .env if present and not already set."""
    # Find project root (4 levels up from modules/ai_agent_orchestration/src/adapters/gemini_adapter.py)
    root = Path(__file__).resolve().parent.parent.parent.parent.parent
    env_file = root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


class GeminiLLMAdapter(LLMAdapter):
    """
    Live Google Gemini LLM adapter conforming to Contract §14.
    Reads API key exclusively from runtime environment (os.environ).
    Gracefully falls back to SmartMockLLMAdapter if network/key issues occur.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash-lite", raise_on_failure: bool = False):
        _load_env()
        # None means "look the key up"; an explicit empty string means "no key",
        # so callers can force the offline path without the ambient environment
        # quietly supplying one.
        self.api_key = (
            os.environ.get("GEMINI_API_KEY", "") if api_key is None else api_key
        ).strip()
        self.model = os.environ.get("GEMINI_MODEL", model)
        self.raise_on_failure = raise_on_failure
        self.fallback = SmartMockLLMAdapter()

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.api_key:
            if self.raise_on_failure:
                raise ValueError("LIVE GEMINI mode selected but GEMINI_API_KEY is not set.")
            logger.info("No GEMINI_API_KEY set; using SmartMockLLMAdapter.")
            return self.fallback.complete(messages, tools)

        # Build contents from messages
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            else:
                gemini_role = "model" if role in ("assistant", "model") else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}]
                })

        # The key goes in a header, never the query string: httpx logs the full
        # request URL at INFO, so ?key=... wrote the secret into the server log
        # (and into Render's retained logs) on every single call.
        headers = {"x-goog-api-key": self.api_key}
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                # A full-length teaching script plus its notes runs well past the
                # small default, and a truncated reply comes back with no parts
                # at all, which used to look like "the model returned nothing".
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        models_to_try = [self.model]
        last_error: Optional[Exception] = None

        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SEC) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                    # Falling through here silently served mock content as if it
                    # were the model's. Say why, so a truncated or blocked reply
                    # is visible in the log instead of looking like a short lesson.
                    reason = (candidates[0].get("finishReason") if candidates else None) or "no candidates"
                    logger.warning(
                        "Gemini '%s' returned no usable text (finishReason=%s, prompt_feedback=%s)",
                        m, reason, data.get("promptFeedback"),
                    )
                    last_error = RuntimeError(f"empty response (finishReason={reason})")
            except Exception as e:
                logger.warning(f"Live Gemini call for '{m}' failed ({e}).")
                last_error = e

        if self.raise_on_failure:
            raise RuntimeError(f"LIVE GEMINI failure: All models failed. Last error: {last_error}")
        return self.fallback.complete(messages, tools)


def get_llm_adapter(api_key: Optional[str] = None) -> LLMAdapter:
    """Factory creating GeminiLLMAdapter if GEMINI_API_KEY is available, else SmartMockLLMAdapter."""
    _load_env()
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if key and key.strip():
        return GeminiLLMAdapter(api_key=key.strip())
    return SmartMockLLMAdapter()
