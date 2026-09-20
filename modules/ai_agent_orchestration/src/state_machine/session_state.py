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
    # Chapters, key terms and excerpts of the source document, so PLAN is
    # grounded in what was uploaded rather than inventing a subject.
    document_outline: Optional[dict] = None
    # The passages that grounded the most recent explanation, so the UI can cite
    # them. Without this the classroom had no citation to display.
    recent_grounding: List[str] = field(default_factory=list)
    # The same passages with their chunk_id/page/section, so a citation can name
    # its source instead of showing a bare excerpt. System-generated from
    # retrieval metadata — never authored by the LLM.
    recent_provenance: List[dict] = field(default_factory=list)
    # 'low' | 'high_hallucination_risk' | 'no_document_context'
    recent_risk_level: str = "low"
