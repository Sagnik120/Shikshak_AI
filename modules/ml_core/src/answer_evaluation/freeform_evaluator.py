import json
import logging
import re
from typing import Optional

from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter
from modules.ml_core.src.embeddings.embedding_client import get_similarity
from modules.ml_core.src.schemas.evaluation import EvaluationResult

logger = logging.getLogger(__name__)

# Similarity bands that let us skip the LLM judge entirely.
CONFIDENTLY_HIGH_THRESHOLD = 0.8
CONFIDENTLY_LOW_THRESHOLD = 0.3

# An answer that demonstrates the core idea counts as correct, even when it
# omits secondary detail. Anything lower is treated as partial understanding.
PASS_CREDIT = 0.7

JUDGE_SYSTEM = (
    "You grade a school student's spoken-style answer against an expected concept. "
    "Grade the understanding shown, not the wording, length, or use of textbook "
    "phrasing. Award credit for the core idea even when secondary detail is missing.\n"
    "Scoring rubric for partial_credit (0.0-1.0):\n"
    "  1.0  fully captures the concept\n"
    "  0.7-0.9  captures the core idea, minor detail missing\n"
    "  0.4-0.6  partially right, or right idea applied to the wrong situation\n"
    "  0.1-0.3  mostly wrong but shows a relevant fragment\n"
    "  0.0  wrong, empty, or off-topic\n"
    f"Set \"correct\" to true when partial_credit >= {PASS_CREDIT}, otherwise false.\n"
    "feedback_text must address the student directly in one or two encouraging "
    "sentences, naming what they got right before what to add.\n"
    'Respond ONLY with JSON: {"correct": bool, "partial_credit": float, "feedback_text": str}'
)


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of a model response that may be fenced or padded."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


class FreeformEvaluator:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter

    def evaluate(
        self,
        node_id: str,
        raw_answer: str,
        expected_concept: str,
        grounding_text: Optional[str] = None,
    ) -> EvaluationResult:
        """Grade a free-text answer: embedding pre-filter, then an LLM rubric judge."""
        answer = (raw_answer or "").strip()
        if not answer:
            return EvaluationResult(
                node_id=node_id,
                correct=False,
                partial_credit=0.0,
                confidence=1.0,
                feedback_text="I didn't catch an answer there — give it a try in your own words.",
            )

        similarity = 0.0
        try:
            target = f"{expected_concept} {grounding_text or ''}".strip()
            similarity = get_similarity(answer, target)
            logger.info("Embedding similarity for node %s: %.3f", node_id, similarity)
        except Exception as exc:
            logger.warning("Embedding check failed (%s); going straight to the LLM judge.", exc)

        if similarity > CONFIDENTLY_HIGH_THRESHOLD:
            return EvaluationResult(
                node_id=node_id,
                correct=True,
                partial_credit=1.0,
                confidence=similarity,
                feedback_text="Exactly right — that's the idea, clearly explained.",
            )

        if 0.0 < similarity < CONFIDENTLY_LOW_THRESHOLD:
            return EvaluationResult(
                node_id=node_id,
                correct=False,
                partial_credit=0.0,
                confidence=1.0 - similarity,
                feedback_text="Not quite — let's look at this concept from another angle.",
            )

        messages = [
            {"role": "system", "content": JUDGE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Expected concept: {expected_concept}\n"
                    f"Source material: {grounding_text or 'None provided'}\n"
                    f"Student answer: {answer}"
                ),
            },
        ]

        try:
            result = _extract_json(self.llm_adapter.complete(messages=messages))
        except Exception as exc:
            logger.error("LLM judge failed for node %s: %s", node_id, exc)
            # Fall back to the embedding signal rather than failing the student
            # outright, which would otherwise trigger needless re-teaching.
            credit = round(min(max(similarity, 0.0), 1.0), 2)
            return EvaluationResult(
                node_id=node_id,
                correct=credit >= PASS_CREDIT,
                partial_credit=credit,
                confidence=0.4,
                feedback_text="Thanks — let's keep going and revisit this if it comes up again.",
            )

        credit = float(result.get("partial_credit", 0.0) or 0.0)
        credit = round(min(max(credit, 0.0), 1.0), 2)

        # Keep `correct` and `partial_credit` consistent: models routinely return
        # "correct": false alongside credit that clearly clears the pass mark.
        correct = bool(result.get("correct", False)) or credit >= PASS_CREDIT
        if correct:
            credit = max(credit, PASS_CREDIT)

        return EvaluationResult(
            node_id=node_id,
            correct=correct,
            partial_credit=credit,
            confidence=0.8,
            feedback_text=result.get("feedback_text") or "Here's your feedback.",
        )
