from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

VALID_TRANSITIONS = {
    TeacherState.UNDERSTAND: [TeacherState.PLAN],
    TeacherState.PLAN: [TeacherState.EXPLAIN],
    TeacherState.EXPLAIN: [TeacherState.DEMONSTRATE],
    TeacherState.DEMONSTRATE: [TeacherState.QUESTION, TeacherState.CONTINUE],
    TeacherState.QUESTION: [TeacherState.EVALUATE],
    TeacherState.EVALUATE: [TeacherState.ADAPT],
    TeacherState.ADAPT: [
        TeacherState.EXPLAIN, 
        TeacherState.PLAN, 
        TeacherState.CONTINUE, 
        TeacherState.HUMAN_ESCALATION
    ],
    TeacherState.CONTINUE: [TeacherState.EXPLAIN, TeacherState.DONE],
    TeacherState.HUMAN_ESCALATION: [TeacherState.DONE],
    TeacherState.DONE: []
}

def is_valid_transition(from_state: TeacherState, to_state: TeacherState) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, [])
