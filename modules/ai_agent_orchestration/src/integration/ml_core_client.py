from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

class MLCoreClient:
    """Stub for the unimplemented ML Core module."""
    
    def evaluate_answer(self, response: StudentResponse) -> EvaluationResult:
        raise NotImplementedError("ML Core is missing. Evaluation logic is not yet implemented.")
