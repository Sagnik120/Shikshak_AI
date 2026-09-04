from typing import Optional, Literal
from pydantic import BaseModel

class EvaluationResult(BaseModel):
    node_id: str
    correct: bool
    partial_credit: float
    misconception_tag: Optional[str] = None
    confidence: float
    feedback_text: str

class AdaptationDecision(BaseModel):
    action: Literal["ALLOW", "MODIFY", "REGENERATE", "HUMAN"]
    target_node_id: str
    reason: str
