import json
import logging
from typing import Optional
from modules.ml_core.src.embeddings.embedding_client import get_similarity
from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter
from modules.ml_core.src.schemas.evaluation import EvaluationResult

logger = logging.getLogger(__name__)

# Thresholds per implementation plan
CONFIDENTLY_HIGH_THRESHOLD = 0.8
CONFIDENTLY_LOW_THRESHOLD = 0.3

class FreeformEvaluator:
    def __init__(self, llm_adapter: LLMAdapter):
        self.llm_adapter = llm_adapter

    def evaluate(
        self, 
        node_id: str, 
        raw_answer: str, 
        expected_concept: str, 
        grounding_text: Optional[str] = None
    ) -> EvaluationResult:
        """Evaluate freeform answers using embedding similarity filter + LLM judge fallback."""
        
        # 1. Fast embedding similarity pre-filter
        similarity = 0.0
        try:
            target_text = f"{expected_concept} {grounding_text or ''}".strip()
            similarity = get_similarity(raw_answer, target_text)
            logger.info(f"Embedding similarity for node {node_id}: {similarity:.3f}")
        except Exception as e:
            logger.warning(f"Embedding check failed: {e}. Falling back to LLM judge.")
            
        # 2. Confident thresholds bypass LLM
        if similarity > CONFIDENTLY_HIGH_THRESHOLD:
            return EvaluationResult(
                node_id=node_id,
                correct=True,
                partial_credit=0.0,
                confidence=similarity,
                feedback_text="Excellent! Your answer is spot on."
            )
            
        if similarity < CONFIDENTLY_LOW_THRESHOLD and similarity > 0.0:
            return EvaluationResult(
                node_id=node_id,
                correct=False,
                partial_credit=0.0,
                confidence=1.0 - similarity,
                feedback_text="Not quite. Let's review this concept again."
            )
            
        # 3. LLM Judge fallback for mid-range (ambiguous) similarity
        messages = [
            {"role": "system", "content": "You are a strict teacher grading a student's answer. Respond ONLY with valid JSON matching: {\"correct\": bool, \"partial_credit\": float (0.0 to 1.0), \"feedback_text\": \"string\"}"},
            {"role": "user", "content": f"Expected Concept: {expected_concept}\nGrounding Text: {grounding_text or 'None'}\nStudent Answer: {raw_answer}"}
        ]
        
        try:
            response_str = self.llm_adapter.complete(messages=messages)
            # Simple cleanup for markdown json blocks if any
            if response_str.startswith("```json"):
                response_str = response_str.strip("`").strip("json").strip()
            result_dict = json.loads(response_str)
            
            return EvaluationResult(
                node_id=node_id,
                correct=result_dict.get("correct", False),
                partial_credit=float(result_dict.get("partial_credit", 0.0)),
                confidence=0.8, # Assumed confidence for LLM judge
                feedback_text=result_dict.get("feedback_text", "Here is your feedback.")
            )
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            # Safe fallback if LLM fails
            return EvaluationResult(
                node_id=node_id,
                correct=False,
                partial_credit=0.0,
                confidence=0.5,
                feedback_text="I could not evaluate your answer properly. Let's try again."
            )
