from typing import Optional
from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ml_core.src.schemas.evaluation import EvaluationResult
from modules.ml_core.src.answer_evaluation.mcq_evaluator import evaluate_mcq
from modules.ml_core.src.answer_evaluation.freeform_evaluator import FreeformEvaluator
from modules.ml_core.src.adapters.llm_adapter_client import LLMAdapter

class AnswerEvaluator:
    """Facade routing evaluation by response_type."""
    
    def __init__(self, llm_adapter: LLMAdapter):
        self.freeform_evaluator = FreeformEvaluator(llm_adapter)
        
    def evaluate(
        self, 
        response: StudentResponse, 
        expected_concept: str, 
        grounding_text: Optional[str] = None
    ) -> EvaluationResult:
        """Route to appropriate evaluator based on response_type."""
        
        # Strict exact match for MCQ
        if response.response_type.lower() == "mcq":
            is_correct = evaluate_mcq(response.raw_answer, expected_concept)
            return EvaluationResult(
                node_id=response.node_id,
                correct=is_correct,
                partial_credit=0.0,
                confidence=1.0, # Deterministic rule match is 100% confident
                feedback_text="Correct!" if is_correct else "Incorrect."
            )
            
        # Freeform for everything else
        return self.freeform_evaluator.evaluate(
            node_id=response.node_id,
            raw_answer=response.raw_answer,
            expected_concept=expected_concept,
            grounding_text=grounding_text
        )
