from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from modules.backend.src.auth import generate_session_token, get_token_header
from modules.backend.src.persistence.in_memory import session_repo
from modules.backend.src.schemas.contract import TopicRequest, LessonPlan
from modules.backend.src.state.driver import SessionDriver
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState

router = APIRouter()

class SessionResponse(BaseModel):
    session_id: str
    token: str

@router.post("/sessions", response_model=SessionResponse)
async def create_session():
    import uuid
    session_id = uuid.uuid4().hex
    token = generate_session_token()
    session_repo.create_session(session_id, token)
    return SessionResponse(session_id=session_id, token=token)

@router.post("/sessions/{session_id}/topic")
async def submit_topic(session_id: str, request: TopicRequest, token: str = Depends(get_token_header)):
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    session_repo.save_topic(session_id, request.topic, request.constraints.model_dump())
    return {"status": "success"}

@router.post("/sessions/{session_id}/plan", response_model=LessonPlan)
async def generate_plan(session_id: str, token: str = Depends(get_token_header)):
    if session_repo.get_session_token(session_id) != token:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    topic_data = session_repo.get_topic_and_constraints(session_id)
    if not topic_data:
        raise HTTPException(status_code=400, detail="Topic not submitted yet")
        
    topic, constraints_dict = topic_data
    from modules.backend.src.schemas.contract import LearnerConstraints
    constraints = LearnerConstraints(**constraints_dict)
    
    driver = SessionDriver(session_id)
    
    # 1. UNDERSTAND
    next_state, _ = driver.step(TeacherState.UNDERSTAND, {
        "constraints": constraints,
        "topic": topic,
        "document_id": None
    })
    
    # 2. PLAN
    next_state, plan = driver.step(next_state, {})
    
    return plan
