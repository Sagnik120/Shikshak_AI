from typing import List
from pydantic import BaseModel

class AssessmentReport(BaseModel):
    lesson_id: str
    score_pct: float
    strong_areas: List[str]
    weak_areas: List[str]
    recommended_next: List[str]
    narrative_feedback: str

class LearnerProfile(BaseModel):
    learner_id: str
    history: List[AssessmentReport]
    strong_concepts: List[str]
    weak_concepts: List[str]
    current_learning_path: List[str]
    preferred_language: str
    preferred_level: str
