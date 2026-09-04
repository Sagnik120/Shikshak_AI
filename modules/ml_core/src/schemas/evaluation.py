from pydantic import BaseModel, Field
from typing import Optional

class EvaluationResult(BaseModel):
    """Evaluation result for a student response matching Contract §10."""
    node_id: str = Field(..., description="The ID of the lesson node.")
    correct: bool = Field(..., description="Whether the answer is fundamentally correct.")
    partial_credit: float = Field(default=0.0, ge=0.0, le=1.0, description="Amount of partial credit (0-1).")
    misconception_tag: Optional[str] = Field(default=None, description="Tag representing a known misconception, if any.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score for the evaluation (0-1).")
    feedback_text: str = Field(..., description="Feedback provided to the student.")
