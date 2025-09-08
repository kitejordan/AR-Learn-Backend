from pydantic import BaseModel
from typing import List, Dict, Optional

class ResolveActionIn(BaseModel):
    modelId: str
    actionId: str
    level: Optional[str] = "beginner"
    mode: Optional[str] = "demo"

class TimelineItem(BaseModel):
    t: int
    effect: str
    params: Dict[str, object] = {}
    target: Optional[str] = None
    path: Optional[List[str]] = None

class ResolveActionOut(BaseModel):
    actionId: str
    timeline: List[TimelineItem]
    labels: List[Dict[str, str]] = []
    narration: List[Dict[str, object]] = []
    sources: List[Dict[str, str]] = []
