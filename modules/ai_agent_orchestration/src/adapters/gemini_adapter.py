import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from modules.ai_agent_orchestration.src.adapters.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)


class SmartMockLLMAdapter(LLMAdapter):
    """
    Deterministic smart fallback LLM adapter that inspects message context
    and returns valid Contract-compliant JSON payloads for offline and testing runs.
    """

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        prompt_text = " ".join(m.get("content", "") for m in messages)
        prompt_lower = prompt_text.lower()

        # 1. Planner Agent -> LessonPlan (Contract §5)
        if "lessonplan" in prompt_lower or "planner" in prompt_lower:
            return json.dumps({
                "lesson_id": "lesson_auto_generated",
                "source": "document" if "document_id" in prompt_lower else "topic",
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

        # 2. Explainer Agent -> TeachingSegment (Contract §6)
        if "teachingsegment" in prompt_lower or "explainer" in prompt_lower:
            cue = "emphasis" if "previous_feedback" in prompt_lower else "neutral"
            return json.dumps({
                "node_id": "node_active",
                "script_text": "Welcome to today's lesson. Let us explore the core principles together step by step.",
                "language": "en",
                "visual_spec": {
                    "type": "equation",
                    "content": "E = mc^2"
                },
                "avatar_cue": cue
            })

        # 3. Questioner Agent -> InteractionEvent (Contract §8)
        if "interactionevent" in prompt_lower or "questioner" in prompt_lower:
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

        # 4. Assessment Agent -> AssessmentReport (Contract §12)
        if "assessmentreport" in prompt_lower or "assessment" in prompt_lower:
            return json.dumps({
                "lesson_id": "lesson_auto_generated",
                "score_pct": 95.0,
                "strong_areas": ["Foundational Principles", "Core Mechanics"],
                "weak_areas": [],
                "recommended_next": ["Advanced Problem Solving"],
                "narrative_feedback": "Outstanding progress! You demonstrated thorough understanding across all lesson checkpoints."
            })

        # 5. ML Core Evaluation / Misconceptions
        if "evaluation" in prompt_lower or "misconception" in prompt_lower:
            return json.dumps({
                "correct": True,
                "confidence": 1.0,
                "partial_credit": 0.0,
                "feedback_text": "Excellent explanation! Your reasoning matches the expected scientific concept."
            })

        # Default fallback
        return json.dumps({"status": "ok", "message": "SmartMock completed"})


class GeminiLLMAdapter(LLMAdapter):
    """
    Live Google Gemini LLM adapter conforming to Contract §14.
    Reads API key exclusively from runtime environment (os.environ).
    Gracefully falls back to SmartMockLLMAdapter if network/key issues occur.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = os.environ.get("GEMINI_MODEL", model)
        self.fallback = SmartMockLLMAdapter()

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.api_key:
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        params = {"key": self.api_key}
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, params=params, json=payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
        except Exception as e:
            logger.warning(f"Live Gemini call failed ({e}); degrading gracefully to SmartMockLLMAdapter.")
            return self.fallback.complete(messages, tools)

        return self.fallback.complete(messages, tools)


def get_llm_adapter(api_key: Optional[str] = None) -> LLMAdapter:
    """Factory creating GeminiLLMAdapter if GEMINI_API_KEY is available, else SmartMockLLMAdapter."""
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if key and key.strip():
        return GeminiLLMAdapter(api_key=key.strip())
    return SmartMockLLMAdapter()
