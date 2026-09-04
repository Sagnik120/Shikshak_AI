import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from modules.backend.src.auth import verify_ws_token
from modules.backend.src.persistence.in_memory import session_repo
from modules.backend.src.state.driver import SessionDriver
from modules.ai_agent_orchestration.src.state_machine.states import TeacherState
from modules.backend.src.schemas.ws import WSMessage
from modules.backend.src.schemas.contract import StudentResponse
from modules.backend.src.integrations.container import services

router = APIRouter()
avatar_service = services["avatar_voice_service"]

@router.websocket("/sessions/{session_id}/live")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str):
    await websocket.accept()
    if not await verify_ws_token(session_id, token, session_repo):
        await websocket.send_json(WSMessage(event_type="error", payload={}, error="Unauthorized").model_dump())
        await websocket.close(code=1008)
        return
        
    driver = SessionDriver(session_id)
    
    # We assume plan is already generated. So we start at EXPLAIN.
    current_state = TeacherState.EXPLAIN
    
    try:
        while True:
            if current_state == TeacherState.EXPLAIN:
                current_state, segment = driver.step(current_state, {})
                # State is now DEMONSTRATE
                
                # DEMONSTRATE step yields a job_id for Avatar rendering
                current_state, payload = driver.step(current_state, {"segment": segment})
                job_id = payload.get("job_id")
                
                # Wait for Avatar render
                while True:
                    status = avatar_service.get_status(job_id)
                    if status and status.status == "done":
                        await websocket.send_json(WSMessage(
                            event_type="video_segment",
                            payload=status.result.model_dump() if hasattr(status.result, "model_dump") else status.result
                        ).model_dump())
                        break
                    elif status and status.status == "failed":
                        await websocket.send_json(WSMessage(event_type="error", payload={}, error=status.error).model_dump())
                        break
                    await asyncio.sleep(1)
                    
                # The orchestrator is now at QUESTION or CONTINUE depending on checkpoint
                
            elif current_state == TeacherState.QUESTION:
                # Generate question
                current_state, question_event = driver.step(current_state, {})
                await websocket.send_json(WSMessage(
                    event_type="interaction_event",
                    payload=question_event.model_dump() if hasattr(question_event, "model_dump") else question_event
                ).model_dump())
                
                # Wait for client response
                data = await websocket.receive_json()
                ws_msg = WSMessage(**data)
                
                if ws_msg.event_type == "student_response":
                    student_resp = StudentResponse(**ws_msg.payload)
                    # Advance from QUESTION to EVALUATE internally handled above,
                    # we need to step EVALUATE
                    current_state, eval_result = driver.step(TeacherState.EVALUATE, {"student_response": student_resp})
                    
                    await websocket.send_json(WSMessage(
                        event_type="evaluation_result",
                        payload=eval_result.model_dump() if hasattr(eval_result, "model_dump") else eval_result
                    ).model_dump())
                    
                    # ADAPT step
                    current_state, decision = driver.step(current_state, {"eval_result": eval_result})
                    
                    await websocket.send_json(WSMessage(
                        event_type="adaptation_decision",
                        payload=decision.model_dump() if hasattr(decision, "model_dump") else decision
                    ).model_dump())
                    
                    # Next state is handled by the Orchestrator loop (EXPLAIN or CONTINUE)
                else:
                    await websocket.send_json(WSMessage(event_type="error", payload={}, error="Expected student_response").model_dump())
                    
            elif current_state == TeacherState.CONTINUE:
                current_state, _ = driver.step(current_state, {})
                
            elif current_state == TeacherState.DONE:
                current_state, report = driver.step(current_state, {})
                await websocket.send_json(WSMessage(
                    event_type="assessment_report",
                    payload=report.model_dump() if hasattr(report, "model_dump") else report
                ).model_dump())
                break
                
            elif current_state == TeacherState.HUMAN_ESCALATION:
                await websocket.send_json(WSMessage(event_type="human_escalation", payload={}).model_dump())
                break
                
    except WebSocketDisconnect:
        pass # Session driver state persists in orchestrator
    except Exception as e:
        await websocket.send_json(WSMessage(event_type="error", payload={}, error=str(e)).model_dump())
        await websocket.close(code=1011)
