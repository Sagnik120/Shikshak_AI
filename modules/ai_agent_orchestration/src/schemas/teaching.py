from typing import Union, Dict, Any, List, Literal, Optional
from pydantic import BaseModel

class VisualSpec(BaseModel):
    type: str
    content: Union[str, Dict[str, Any]]

class SegmentNotes(BaseModel):
    """Chapter notes for the board below the video. Restates the script only."""
    key_points: List[str] = []
    example: Optional[str] = None

class TeachingSegment(BaseModel):
    node_id: str
    script_text: str
    language: str
    visual_spec: VisualSpec
    avatar_cue: Literal["neutral", "emphasis", "questioning"]
    # Optional so older payloads (and the mock adapter) still validate.
    notes: Optional[SegmentNotes] = None
