from typing import List, Optional, Any
from dataclasses import dataclass, field
from modules.ai_agent_orchestration.src.schemas.lesson import LessonPlan, LearnerConstraints
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

@dataclass
class SessionState:
    session_id: str
    lesson_plan: Optional[LessonPlan] = None
    current_node_index: int = 0
    evaluation_history: List[EvaluationResult] = field(default_factory=list)
    state_logs: List[dict] = field(default_factory=list)
    constraints: Optional[LearnerConstraints] = None
    topic: Optional[str] = None
    document_id: Optional[str] = None
    current_feedback_override: Optional[str] = None
    recent_segment: Optional[Any] = None
    recent_question: Optional[Any] = None
