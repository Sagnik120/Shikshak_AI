import uuid
from fastapi import Header, HTTPException, Query

def generate_session_token() -> str:
    return uuid.uuid4().hex

def verify_token(session_id: str, token: str, session_repo) -> bool:
    expected_token = session_repo.get_session_token(session_id)
    if not expected_token:
        return False
    return expected_token == token

async def get_token_header(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")
    return authorization.split("Bearer ")[1]

async def verify_ws_token(session_id: str, token: str = Query(None), session_repo=None):
    if not token or not session_repo:
        return False
    return verify_token(session_id, token, session_repo)
