from typing import Optional, Dict, Any, Tuple
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.ai_agent_orchestration.src.state_machine.session_state import SessionState
from modules.ai_agent_orchestration.src.state_machine.transitions import is_valid_transition
from modules.ai_agent_orchestration.src.logging_utils import log_transition

from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent

class TeacherOrchestrator:
    def __init__(
        self,
        planner: PlannerAgent,
        explainer: ExplainerAgent,
        questioner: QuestionerAgent,
        controller: AdaptationController,
        assessor: AssessmentAgent,
        rag_client: Any,
        ml_core_client: Any,
        avatar_client: Any
    ):
        self.planner = planner
        self.explainer = explainer
        self.questioner = questioner
        self.controller = controller
        self.assessor = assessor
        self.rag_client = rag_client
        self.ml_core = ml_core_client
        self.avatar_client = avatar_client

    def _transition(self, session: SessionState, from_state: TeacherState, to_state: TeacherState, reason: str, payload: Any = None) -> Tuple[TeacherState, Any]:
        if not is_valid_transition(from_state, to_state):
            raise ValueError(f"Invalid transition from {from_state} to {to_state}")
        
        log = log_transition(session.session_id, from_state, to_state, reason, {"payload": str(payload)})
        session.state_logs.append(log)
        return to_state, payload

    def step(self, current_state: TeacherState, session: SessionState, inputs: Dict[str, Any]) -> Tuple[TeacherState, Any]:
        """Execute one step of the FSM based on current state."""
        
        if current_state == TeacherState.UNDERSTAND:
            # Inputs: constraints, topic, document_id
            session.constraints = inputs.get("constraints")
            session.topic = inputs.get("topic")
            session.document_id = inputs.get("document_id")
            return self._transition(session, current_state, TeacherState.PLAN, "Context initialized")

        elif current_state == TeacherState.PLAN:
            source_type = "document" if session.document_id else "topic"
            plan = self.planner.plan_lesson(
                constraints=session.constraints,
                source_type=source_type,
                topic=session.topic
            )
            session.lesson_plan = plan
            session.current_node_index = 0
            return self._transition(session, current_state, TeacherState.EXPLAIN, "Lesson plan generated", plan)

        elif current_state == TeacherState.EXPLAIN:
            node = session.lesson_plan.nodes[session.current_node_index]
            
            chunks = None
            if session.document_id:
                chunks = self.rag_client.retrieve_context(session.document_id, node.concept)
                
            segment = self.explainer.generate_segment(
                node=node,
                constraints=session.constraints,
                grounding_chunks=chunks,
                previous_feedback=session.current_feedback_override
            )
            # Clear override after use
            session.current_feedback_override = None
            
            return self._transition(session, current_state, TeacherState.DEMONSTRATE, "Explanation segment generated", segment)

        elif current_state == TeacherState.DEMONSTRATE:
            segment = inputs.get("segment")
            job_id = self.avatar_client.render_segment(segment)
            node = session.lesson_plan.nodes[session.current_node_index]
            
            if node.checkpoint_question:
                return self._transition(session, current_state, TeacherState.QUESTION, "Video enqueued, moving to question", {"job_id": job_id})
            else:
                return self._transition(session, current_state, TeacherState.CONTINUE, "Video enqueued, skipping question", {"job_id": job_id})

        elif current_state == TeacherState.QUESTION:
            node = session.lesson_plan.nodes[session.current_node_index]
            recent_segment = inputs.get("segment")
            event = self.questioner.generate_question(node, recent_segment)
            return self._transition(session, current_state, TeacherState.EVALUATE, "Question generated", event)

        elif current_state == TeacherState.EVALUATE:
            student_response = inputs.get("student_response")
            node = session.lesson_plan.nodes[session.current_node_index] if session.lesson_plan and session.lesson_plan.nodes else None
            concept = node.concept if node else ""
            eval_result = self.ml_core.evaluate_answer(student_response, expected_concept=concept)
            session.evaluation_history.append(eval_result)
            return self._transition(session, current_state, TeacherState.ADAPT, "Answer evaluated", eval_result)

        elif current_state == TeacherState.ADAPT:
            eval_result = inputs.get("eval_result")
            decision = self.controller.decide(eval_result, session.evaluation_history)
            
            if decision.action == "ALLOW":
                return self._transition(session, current_state, TeacherState.CONTINUE, decision.reason, decision)
            elif decision.action == "MODIFY":
                session.current_feedback_override = decision.reason
                return self._transition(session, current_state, TeacherState.EXPLAIN, decision.reason, decision)
            elif decision.action == "REGENERATE":
                return self._transition(session, current_state, TeacherState.PLAN, decision.reason, decision)
            elif decision.action == "HUMAN":
                return self._transition(session, current_state, TeacherState.HUMAN_ESCALATION, decision.reason, decision)

        elif current_state == TeacherState.CONTINUE:
            session.current_node_index += 1
            if session.current_node_index >= len(session.lesson_plan.nodes):
                return self._transition(session, current_state, TeacherState.DONE, "All nodes completed")
            else:
                return self._transition(session, current_state, TeacherState.EXPLAIN, "Moving to next node")

        elif current_state == TeacherState.DONE:
            report = self.assessor.generate_report(session.lesson_plan.lesson_id, session.evaluation_history)
            return current_state, report
            
        elif current_state == TeacherState.HUMAN_ESCALATION:
            return current_state, None
            
        raise ValueError(f"Unhandled state: {current_state}")
