from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float = Field(..., ge=0)
