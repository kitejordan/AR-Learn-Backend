from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class GenerateQuizIn(BaseModel):
    model_id: Optional[str] = Field(None, description="Preferred: exact model id")
    model_name: Optional[str] = Field(None, description="Fallback: human-readable name")
    num_questions: int = Field(5, ge=1, le=10)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    # optional: narrow the scope (e.g., only parts the user has seen)
    include_parts: Optional[List[str]] = None   # exact Part.name matches if provided

class MCQ(BaseModel):
    id: str
    stem: str
    options: List[str]          # 3–6 options, typically 4
    correct_index: int          # 0-based
    explanation: Optional[str] = None
    sources: List[str] = []     # part/process names used to form the question

class GenerateQuizOut(BaseModel):
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    difficulty: str
    questions: List[MCQ]
