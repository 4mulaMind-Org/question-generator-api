from pydantic import BaseModel, Field
from datetime import datetime


class QuestionCreate(BaseModel):
    content: str = Field(..., min_length=5)
    tags: str = ""


class QuestionOut(BaseModel):
    id: int
    content: str
    tags: str
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateCheckRequest(BaseModel):
    content: str = Field(..., min_length=5)
    threshold: float = 0.85


class DuplicateMatch(BaseModel):
    id: int
    content: str
    similarity: float


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    match_type: str          # exact | semantic | none
    top_match: DuplicateMatch | None = None
    all_matches: list[DuplicateMatch] = []

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    max_attempts: int = 5
    threshold: float = 0.85


class GenerationAttempt(BaseModel):
    attempt: int
    candidate: str
    is_duplicate: bool
    match_type: str
    similarity: float | None = None


class GenerateResponse(BaseModel):
    success: bool
    question: str | None = None
    attempts: list[GenerationAttempt]
    total_attempts: int
    reason: str | None = None