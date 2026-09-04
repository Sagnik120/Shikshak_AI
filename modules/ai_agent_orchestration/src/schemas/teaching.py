from typing import Union, Dict, Any, Literal
from pydantic import BaseModel

class VisualSpec(BaseModel):
    type: str
    content: Union[str, Dict[str, Any]]

class TeachingSegment(BaseModel):
    node_id: str
    script_text: str
    language: str
    visual_spec: VisualSpec
    avatar_cue: Literal["neutral", "emphasis", "questioning"]
