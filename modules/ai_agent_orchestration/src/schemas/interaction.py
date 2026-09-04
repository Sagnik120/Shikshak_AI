from typing import List, Literal
from pydantic import BaseModel

class InteractionEvent(BaseModel):
    node_id: str
    question_text: str
    type: Literal["mcq", "short_answer", "problem", "application", "explain_in_own_words"]
    options: List[str]
    expected_concept: str

class StudentResponse(BaseModel):
    node_id: str
    raw_answer: str
    response_type: str
    response_time_sec: float
