import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from modules.ai_agent_orchestration.src.adapters.gemini_adapter import (
    GeminiLLMAdapter,
    SmartMockLLMAdapter,
    get_llm_adapter
)
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.service import AIOperationService
from modules.ai_agent_orchestration.src.schemas.lesson import (
    LearnerConstraints,
    LessonNode,
    LessonPlan
)
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment, VisualSpec
from modules.ai_agent_orchestration.src.schemas.interaction import InteractionEvent, StudentResponse
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult, AdaptationDecision
from modules.ai_agent_orchestration.src.schemas.assessment import AssessmentReport
from modules.ai_agent_orchestration.tests.web_test.logger import test_logger

app = FastAPI(
    title="Shikshak AI — AI Agent Orchestration Isolated Testbed",
    description="Dedicated testing backend for isolated human & programmatic evaluation of the orchestration module",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper / Mock Client Stubs for Isolated FSM Testing
# ---------------------------------------------------------------------------

class IsolatedRAGClientStub:
    """Mock RAG client for standalone FSM stepping."""
    def retrieve_context(self, document_id: str, concept: str) -> List[Any]:
        return [f"Key context for concept '{concept}' extracted from document {document_id}."]


class IsolatedMLCoreClientStub:
    """Mock ML Core client for standalone FSM stepping."""
    def evaluate_answer(self, student_response: Any, expected_concept: str = "") -> EvaluationResult:
        resp_str = str(student_response).lower()
        is_wrong = any(w in resp_str for w in ["wrong", "incorrect", "false", "confused", "accelerat"])
        is_partial = "partial" in resp_str or "somewhat" in resp_str

        if is_wrong:
            return EvaluationResult(
                node_id="test_node",
                correct=False,
                partial_credit=0.0,
                misconception_tag="misconception_force_velocity_confusion",
                confidence=0.92,
                feedback_text="Identified misconception: Velocity confused with net force."
            )
        elif is_partial:
            return EvaluationResult(
                node_id="test_node",
                correct=False,
                partial_credit=0.5,
                misconception_tag=None,
                confidence=0.75,
                feedback_text="Partially correct reasoning, but omitted units or boundary conditions."
            )
        else:
            return EvaluationResult(
                node_id="test_node",
                correct=True,
                partial_credit=1.0,
                misconception_tag=None,
                confidence=0.98,
                feedback_text="Excellent explanation! Matches expected scientific concept."
            )


class IsolatedAvatarClientStub:
    """Mock Avatar client for standalone FSM stepping."""
    def render_segment(self, segment: Any) -> str:
        return "simulated_avatar_job_id_12345"


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class PlannerTestRequest(BaseModel):
    topic: Optional[str] = "Newton's Laws of Motion"
    level: str = "beginner"
    language: str = "en"
    time_budget_min: Union[int, str] = 15
    style: Optional[str] = "conceptual"
    document_text: Optional[str] = None
    use_live_llm: bool = True


class ExplainerTestRequest(BaseModel):
    concept: str = "Newton's First Law (Law of Inertia)"
    depth: str = "core"
    visual_type: str = "diagram"
    level: str = "beginner"
    language: str = "en"
    time_budget_min: int = 15
    grounding_chunks: Optional[List[str]] = None
    previous_feedback: Optional[str] = None
    use_live_llm: bool = True


class QuestionerTestRequest(BaseModel):
    concept: str = "Newton's First Law (Law of Inertia)"
    depth: str = "core"
    visual_type: str = "diagram"
    recent_script: Optional[str] = None
    use_live_llm: bool = True


class AdaptationTestRequest(BaseModel):
    node_id: str = "node_1"
    correct: bool = False
    partial_credit: float = 0.0
    misconception_tag: Optional[str] = "force_velocity_confusion"
    confidence: float = 0.85
    feedback_text: str = "Student confused velocity with acceleration."
    consecutive_failures_on_node: int = 1


class AssessmentTestRequest(BaseModel):
    lesson_id: str = "lesson_demo_1"
    session_history: List[Dict[str, Any]] = Field(default_factory=list)
    use_live_llm: bool = True


class FSMStepRequest(BaseModel):
    session_id: str = "session_test_01"
    current_state: str = "UNDERSTAND"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    use_live_llm: bool = True


# In-memory FSM session store for isolated stepping
fsm_sessions: Dict[str, SessionState] = {}


def _get_adapter(use_live: bool):
    if use_live and os.environ.get("GEMINI_API_KEY"):
        return GeminiLLMAdapter()
    return SmartMockLLMAdapter()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/test/status")
def get_testbed_status():
    """Return operational status, active LLM config, and log statistics."""
    has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

    log_counts = {}
    for cat in test_logger.CATEGORIES:
        cat_dir = test_logger.base_dir / cat
        log_counts[cat] = len(list(cat_dir.glob("*.json"))) if cat_dir.exists() else 0

    return {
        "status": "ready",
        "gemini_api_key_configured": has_key,
        "default_model": model,
        "log_directory": str(test_logger.base_dir),
        "log_counts": log_counts,
        "server_port": 8001
    }


@app.post("/api/test/planner")
def test_planner(req: PlannerTestRequest):
    """Test PlannerAgent.plan_lesson() with structured execution logging."""
    trace = test_logger.start_trace("planner", "plan_lesson", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/planner.py", "plan_lesson", "start")

    try:
        adapter = _get_adapter(req.use_live_llm)
        agent = PlannerAgent(llm_adapter=adapter)

        # Handle time budget typing
        time_budget = req.time_budget_min
        if isinstance(time_budget, str) and time_budget.isdigit():
            time_budget = int(time_budget)
        elif time_budget != "multi_day_plan":
            try:
                time_budget = int(time_budget)
            except Exception:
                time_budget = 15

        constraints = LearnerConstraints(
            level=req.level,  # type: ignore
            language=req.language,
            time_budget_min=time_budget,  # type: ignore
            style=req.style
        )

        trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/planner.py", "plan_lesson", "constraints_built")

        parsed_doc_stub = None
        if req.document_text:
            class DocStub:
                detected_structure = req.document_text[:400]
            parsed_doc_stub = DocStub()

        plan = agent.plan_lesson(
            constraints=constraints,
            source_type="document" if req.document_text else "topic",
            topic=req.topic,
            parsed_doc=parsed_doc_stub
        )

        trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/planner.py", "plan_lesson", "plan_validated")
        trace.set_output(plan)
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "duration_ms": manifest["duration_ms"],
            "plan": plan.model_dump()
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.post("/api/test/explainer")
def test_explainer(req: ExplainerTestRequest):
    """Test ExplainerAgent.generate_segment() with structured execution logging."""
    trace = test_logger.start_trace("explainer", "generate_segment", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/explainer.py", "generate_segment", "start")

    try:
        adapter = _get_adapter(req.use_live_llm)
        agent = ExplainerAgent(llm_adapter=adapter)

        node = LessonNode(
            node_id="test_node_01",
            concept=req.concept,
            depth=req.depth,  # type: ignore
            est_minutes=5,
            visual_type=req.visual_type,  # type: ignore
            checkpoint_question=True
        )

        constraints = LearnerConstraints(
            level=req.level,  # type: ignore
            language=req.language,
            time_budget_min=req.time_budget_min
        )

        chunks = None
        if req.grounding_chunks:
            class ChunkStub:
                def __init__(self, t):
                    self.text = t
            chunks = [ChunkStub(c) for c in req.grounding_chunks]

        segment = agent.generate_segment(
            node=node,
            constraints=constraints,
            grounding_chunks=chunks,
            previous_feedback=req.previous_feedback
        )

        trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/explainer.py", "generate_segment", "segment_validated")
        trace.set_output(segment)
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "duration_ms": manifest["duration_ms"],
            "segment": segment.model_dump()
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.post("/api/test/questioner")
def test_questioner(req: QuestionerTestRequest):
    """Test QuestionerAgent.generate_question() with structured execution logging."""
    trace = test_logger.start_trace("questioner", "generate_question", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/questioner.py", "generate_question", "start")

    try:
        adapter = _get_adapter(req.use_live_llm)
        agent = QuestionerAgent(llm_adapter=adapter)

        node = LessonNode(
            node_id="test_node_01",
            concept=req.concept,
            depth=req.depth,  # type: ignore
            est_minutes=5,
            visual_type=req.visual_type,  # type: ignore
            checkpoint_question=True
        )

        segment = None
        if req.recent_script:
            segment = TeachingSegment(
                node_id="test_node_01",
                script_text=req.recent_script,
                language="en",
                visual_spec=VisualSpec(type="diagram", content="Sample visual"),
                avatar_cue="neutral"
            )

        question = agent.generate_question(node=node, recent_segment=segment)

        trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/questioner.py", "generate_question", "question_validated")
        trace.set_output(question)
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "duration_ms": manifest["duration_ms"],
            "question": question.model_dump()
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.post("/api/test/adaptation")
def test_adaptation(req: AdaptationTestRequest):
    """Test AdaptationController.decide() with rule evaluation tracing."""
    trace = test_logger.start_trace("adaptation", "decide", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/adaptation_controller.py", "decide", "start")

    try:
        controller = AdaptationController()

        current_eval = EvaluationResult(
            node_id=req.node_id,
            correct=req.correct,
            partial_credit=req.partial_credit,
            misconception_tag=req.misconception_tag if not req.correct else None,
            confidence=req.confidence,
            feedback_text=req.feedback_text
        )

        # Build simulated history
        history: List[EvaluationResult] = []
        for _ in range(max(0, req.consecutive_failures_on_node - 1)):
            history.append(EvaluationResult(
                node_id=req.node_id,
                correct=False,
                partial_credit=0.0,
                misconception_tag=req.misconception_tag,
                confidence=0.8,
                feedback_text="Previous failure"
            ))

        decision = controller.decide(current_eval=current_eval, session_history=history)

        trace.add_checkpoint(
            "modules/ai_agent_orchestration/src/agents/adaptation_controller.py",
            "decide",
            "decision_made",
            {"action": decision.action, "reason": decision.reason}
        )
        trace.set_output(decision)
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "duration_ms": manifest["duration_ms"],
            "decision": decision.model_dump()
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.post("/api/test/assessment")
def test_assessment(req: AssessmentTestRequest):
    """Test AssessmentAgent.generate_report() with structured execution logging."""
    trace = test_logger.start_trace("assessment", "generate_report", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/assessment.py", "generate_report", "start")

    try:
        adapter = _get_adapter(req.use_live_llm)
        agent = AssessmentAgent(llm_adapter=adapter)

        # Convert dict items into EvaluationResults
        eval_history: List[EvaluationResult] = []
        if req.session_history:
            for item in req.session_history:
                eval_history.append(EvaluationResult.model_validate(item))
        else:
            # Default rich sample history
            eval_history = [
                EvaluationResult(
                    node_id="node_1",
                    correct=True,
                    partial_credit=1.0,
                    misconception_tag=None,
                    confidence=0.95,
                    feedback_text="Correct answer on Newton's First Law."
                ),
                EvaluationResult(
                    node_id="node_2",
                    correct=False,
                    partial_credit=0.5,
                    misconception_tag="force_velocity_confusion",
                    confidence=0.80,
                    feedback_text="Misconception on acceleration vector vs velocity."
                ),
                EvaluationResult(
                    node_id="node_2_retry",
                    correct=True,
                    partial_credit=1.0,
                    misconception_tag=None,
                    confidence=0.90,
                    feedback_text="Mastered concept after analogy modification."
                )
            ]

        report = agent.generate_report(lesson_id=req.lesson_id, session_history=eval_history)

        trace.add_checkpoint("modules/ai_agent_orchestration/src/agents/assessment.py", "generate_report", "report_validated")
        trace.set_output(report)
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "duration_ms": manifest["duration_ms"],
            "report": report.model_dump()
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.post("/api/test/fsm/step")
def test_fsm_step(req: FSMStepRequest):
    """Execute one step of the TeacherOrchestrator FSM and return next state and payload."""
    trace = test_logger.start_trace("fsm", "orchestrator_step", req.model_dump())
    trace.add_checkpoint("modules/ai_agent_orchestration/src/state_machine/orchestrator.py", "step", "start")

    try:
        adapter = _get_adapter(req.use_live_llm)

        # Build agents
        planner = PlannerAgent(llm_adapter=adapter)
        explainer = ExplainerAgent(llm_adapter=adapter)
        questioner = QuestionerAgent(llm_adapter=adapter)
        controller = AdaptationController()
        assessor = AssessmentAgent(llm_adapter=adapter)

        orchestrator = TeacherOrchestrator(
            planner=planner,
            explainer=explainer,
            questioner=questioner,
            controller=controller,
            assessor=assessor,
            rag_client=IsolatedRAGClientStub(),
            ml_core_client=IsolatedMLCoreClientStub(),
            avatar_client=IsolatedAvatarClientStub()
        )

        # Get or init session
        if req.session_id not in fsm_sessions:
            fsm_sessions[req.session_id] = SessionState(session_id=req.session_id)
        session = fsm_sessions[req.session_id]

        state_enum = getattr(TeacherState, req.current_state)
        next_state, payload = orchestrator.step(state_enum, session, req.inputs)

        output_payload = payload
        if hasattr(payload, "model_dump"):
            output_payload = payload.model_dump()
        elif isinstance(payload, dict):
            output_payload = payload
        else:
            output_payload = str(payload)

        trace.add_checkpoint(
            "modules/ai_agent_orchestration/src/state_machine/orchestrator.py",
            "step",
            "transition_complete",
            {"from": req.current_state, "to": next_state.name}
        )
        trace.set_output({"next_state": next_state.name, "payload": output_payload})
        manifest = trace.finish()

        return {
            "success": True,
            "run_id": manifest["run_id"],
            "session_id": session.session_id,
            "previous_state": req.current_state,
            "next_state": next_state.name,
            "current_node_index": session.current_node_index,
            "payload": output_payload,
            "state_logs": session.state_logs[-5:]
        }

    except Exception as e:
        trace.set_error(e)
        manifest = trace.finish()
        raise HTTPException(status_code=500, detail={"error": str(e), "run_id": manifest["run_id"]})


@app.get("/api/test/logs")
def get_recent_logs(category: Optional[str] = None, limit: int = Query(default=30, le=100)):
    """List recent execution logs from tests/web_test/logs/."""
    return test_logger.list_recent_logs(category=category, limit=limit)


@app.get("/api/test/logs/{category}/{filename}")
def get_log_details(category: str, filename: str):
    """Retrieve full JSON content of a specific test execution log."""
    content = test_logger.get_log_content(category, filename)
    if not content:
        raise HTTPException(status_code=404, detail=f"Log file '{filename}' not found in '{category}'.")
    return content


# ---------------------------------------------------------------------------
# Mount Static Frontend
# ---------------------------------------------------------------------------
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main():
    """Launch the isolated test server on port 8001."""
    print("=" * 70)
    print("  SHIKSHAK AI — ORCHESTRATION ISOLATED WEB TESTBED")
    print("  Running on: http://localhost:8001")
    print("  Testing Code: modules/ai_agent_orchestration/src/")
    print("  Production Backend (Port 8000) remains 100% untouched.")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
