from typing import List, Optional, Literal, Union
from pydantic import BaseModel

class LearnerConstraints(BaseModel):
    level: Literal["beginner", "intermediate", "advanced"]
    language: str
    time_budget_min: Union[int, Literal["multi_day_plan"]]
    style: Optional[str] = None

class LessonNode(BaseModel):
    node_id: str
    concept: str
    depth: Literal["intro", "core", "advanced"]
    est_minutes: int
    visual_type: Literal["equation", "graph", "diagram", "code", "image", "timeline", "map", "simulation"]
    checkpoint_question: bool

class LessonPlan(BaseModel):
    lesson_id: str
    source: Literal["document", "topic"]
    constraints: LearnerConstraints
    nodes: List[LessonNode]
