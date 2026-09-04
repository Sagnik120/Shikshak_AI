from typing import Any, Optional
from pydantic import BaseModel

class WSMessage(BaseModel):
    event_type: str
    payload: Any
    error: Optional[str] = None
