from pydantic import BaseModel, Field


class LatencyMetrics(BaseModel):
    stt_ms: int = Field(..., ge=0)
    llm_ms: int = Field(..., ge=0)
    tts_ms: int = Field(..., ge=0)
    total_ms: int = Field(..., ge=0)


class VoiceDebugResponse(BaseModel):
    transcription: str
    llm_response: str
    audio_file_path: str
    latency: LatencyMetrics
    end_call: bool = False
    call_id: str | None = None
    turn_number: int | None = None
    session_id: str | None = None
