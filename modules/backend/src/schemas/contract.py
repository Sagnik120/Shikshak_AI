from typing import Optional, List, Union, Literal
from pydantic import BaseModel, Field

class LearnerConstraints(BaseModel):
    level: Literal["beginner", "intermediate", "advanced"]
    language: str
    time_budget_min: Union[int, Literal["multi_day_plan"]]
    style: Optional[str] = None

class UploadRequest(BaseModel):
    session_id: str
    constraints: LearnerConstraints

class TopicRequest(BaseModel):
    session_id: str
    topic: str
    constraints: LearnerConstraints

class ChunkInfo(BaseModel):
    chunk_id: str
    text: str
    section_title: Optional[str] = None
    page_or_slide: Optional[int] = None
    embedding_ref: str

class DocumentStructure(BaseModel):
    chapters: List[str]
    key_terms: List[str]

class ParsedDocument(BaseModel):
    document_id: str
    source_lang: str
    chunks: List[ChunkInfo]
    detected_structure: DocumentStructure

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

class VisualSpec(BaseModel):
    type: str
    content: Union[str, dict]

class TeachingSegment(BaseModel):
    node_id: str
    script_text: str
    language: str
    visual_spec: VisualSpec
    avatar_cue: Literal["neutral", "emphasis", "questioning", "encouraging", "celebratory"]

class RenderedVideoSegment(BaseModel):
    node_id: str
    video_url: str
    duration_sec: float
    captions_vtt_url: Optional[str] = None

class InteractionEvent(BaseModel):
    node_id: str
    question_text: str
    type: Literal["mcq", "short_answer", "problem", "application", "explain_in_own_words"]
    options: List[str] = Field(default_factory=list)
    expected_concept: str

class StudentResponse(BaseModel):
    node_id: str
    raw_answer: str
    response_type: str
    response_time_sec: float

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
