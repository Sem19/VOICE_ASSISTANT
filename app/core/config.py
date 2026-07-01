from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "local-voice-ai-assistant"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    STT_MODEL_SIZE: str = "base"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_LANGUAGE: str = "en"
    TTS_PROVIDER: str = "piper"
    PIPER_MODEL_PATH: str = "models/piper/en_US-lessac-medium.onnx"
    PIPER_CONFIG_PATH: str = "models/piper/en_US-lessac-medium.onnx.json"
    TTS_OUTPUT_DIR: str = "storage/tts"
    VOICE_MAX_TURNS: int = 5
    VOICE_GREETING: str = (
        "Hello! I'm your voice assistant. "
        "Ask me a question after the beep, and say goodbye when you're finished."
    )
    VOICE_THINKING_PROMPT: str = "One moment please, I'm thinking."


settings = Settings()
