# local-voice-ai-assistant

Backend for a local Voice AI Assistant. Phase 1 provides infrastructure. Phase 2 adds LLM chat via Ollama. Phase 3 adds local speech-to-text with faster-whisper. Phase 4 adds local text-to-speech with Piper. Phase 5 connects STT, LLM, and TTS into a single voice pipeline. Telephony integrations are planned for later phases.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker and Docker Compose (recommended — includes Ollama)
- [Ollama](https://ollama.com/) on the host (optional — only if running the API locally with `uv run`)

## Install uv

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:

```bash
uv --version
```

## Configuration

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

On Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Available settings:

| Variable         | Description                          | Default                      |
|------------------|--------------------------------------|------------------------------|
| APP_NAME         | Application name                     | local-voice-ai-assistant     |
| ENV              | Environment (development/production) | development                  |
| LOG_LEVEL        | Logging level                        | INFO                         |
| API_HOST         | Host to bind the API server          | 0.0.0.0                      |
| API_PORT         | Port for the API server              | 8000                         |
| OLLAMA_BASE_URL  | Ollama API base URL                  | http://localhost:11434 (local) / set automatically in Docker Compose |
| OLLAMA_MODEL     | Ollama model name                    | llama3.2                     |
| STT_MODEL_SIZE   | faster-whisper model size            | base                         |
| STT_DEVICE       | Inference device                     | cpu                          |
| STT_COMPUTE_TYPE | faster-whisper compute type          | int8                         |
| TTS_PROVIDER     | TTS provider                         | piper                        |
| PIPER_MODEL_PATH | Path to Piper ONNX model             | models/piper/en_US-lessac-medium.onnx |
| PIPER_CONFIG_PATH| Path to Piper model config JSON      | models/piper/en_US-lessac-medium.onnx.json |
| TTS_OUTPUT_DIR   | Directory for generated WAV files    | storage/tts                  |

## Run locally

Install dependencies and start the server:

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "local-voice-ai-assistant"
}
```

### Chat (local run with `uv`)

Requires Ollama installed on your machine. Start Ollama and pull a model (if needed):

```bash
ollama pull llama3.2
```

Send a chat message:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello\"}"
```

Expected response:

```json
{
  "response": "Hello! How can I help you?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Use the returned `session_id` in follow-up requests to keep conversation history in memory:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What did I just say?\", \"session_id\": \"550e8400-e29b-41d4-a716-446655440000\"}"
```

If Ollama is not running, the API returns HTTP 503.

### Transcribe (Phase 3)

Upload an audio file for local transcription. Supported formats: **wav**, **mp3**, **m4a**, **flac**.

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@sample.wav"
```

Expected response:

```json
{
  "text": "recognized speech",
  "language": "en",
  "duration_seconds": 4.2
}
```

The faster-whisper model is lazy-loaded on the first transcription request. The first request may take longer while the model downloads and loads.

You can also use [http://localhost:8000/docs](http://localhost:8000/docs) → **POST /transcribe**.

### Text-to-Speech (Phase 4)

Convert text to a WAV audio file using Piper TTS.

Download a Piper voice model (one time). The ONNX file must be about **63 MB** — a smaller file means the download was incomplete.

```bash
docker compose exec voice-ai-backend uv run python -m piper.download_voices en_US-lessac-medium --download-dir models/piper
```

Verify the download:

```bash
docker compose exec voice-ai-backend ls -la models/piper/
```

You should see `en_US-lessac-medium.onnx` at roughly **63201294 bytes**. If the file is smaller, delete it and download again.

For local runs without Docker:

```bash
uv run python -m piper.download_voices en_US-lessac-medium --download-dir models/piper
```

Send text for synthesis:

```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Hello, how can I help you?\"}" \
  --output speech.wav
```

The response is a **WAV audio file**. Generated files are also saved under `storage/tts/`.

Use [http://localhost:8000/docs](http://localhost:8000/docs) → **POST /tts** to try it in the browser.

If Piper model files are missing, the API returns HTTP 503.

### Voice pipeline (Phase 5)

Send an audio file and receive a spoken AI response in one request:

```
audio upload → STT → LLM → TTS → WAV response
```

```bash
curl -X POST http://localhost:8000/voice \
  -F "file=@sample.wav" \
  -F "session_id=demo-session" \
  --output ai_response.wav
```

The response is a **WAV audio file** with the assistant's spoken reply.

Debug mode returns JSON with transcription, LLM response, audio path, and latency breakdown:

```bash
curl -X POST http://localhost:8000/voice \
  -F "file=@sample.wav" \
  -F "session_id=demo-session" \
  -F "return_debug=true"
```

Example debug response:

```json
{
  "transcription": "user recognized text",
  "llm_response": "assistant answer",
  "audio_file_path": "storage/tts/8950a4e2-c809-4ac7-9595-5d16fcaea287.wav",
  "latency": {
    "stt_ms": 1234,
    "llm_ms": 2345,
    "tts_ms": 987,
    "total_ms": 4566
  }
}
```

Use [http://localhost:8000/docs](http://localhost:8000/docs) → **POST /voice** to try it in the browser.

Supported upload formats: **wav**, **mp3**, **m4a**, **flac**. Optional `session_id` keeps conversation history across requests.

## Run with Docker Compose

Docker Compose runs **both** the API and **Ollama** — no local Ollama install needed.

Ensure `.env` exists (copy from `.env.example`), then:

```bash
docker compose up --build
```

On first run, pull the model into the Ollama container (one time):

```bash
docker compose exec ollama ollama pull llama3.2
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs) and try **POST /chat**.

Services:

| Service            | URL                                      |
|--------------------|------------------------------------------|
| API                | [http://localhost:8000](http://localhost:8000) |
| Ollama (optional)  | [http://localhost:11434](http://localhost:11434) |

The backend connects to Ollama at `http://ollama:11434` inside the Docker network. Your `.env` `OLLAMA_BASE_URL` is overridden automatically in Compose — you do not need `host.docker.internal`.

Model files are stored in the `ollama_data` Docker volume and persist across restarts.

## Run tests

```bash
uv sync --group dev
uv run pytest
```

## Project structure

```
local-voice-ai-assistant/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/
│   │   ├── health.py        # Health check endpoint
│   │   ├── chat.py          # Chat endpoint
│   │   ├── transcribe.py    # Speech-to-text endpoint
│   │   ├── tts.py           # Text-to-speech endpoint
│   │   ├── voice.py         # End-to-end voice pipeline
│   │   └── deps.py          # Dependency injection
│   ├── core/config.py       # Settings from .env
│   ├── core/logging.py      # Structured logging setup
│   ├── services/
│   │   ├── chat.py          # Session-aware chat orchestration
│   │   ├── llm/
│   │   │   ├── base.py      # LLMService abstraction
│   │   │   └── ollama.py    # Ollama implementation
│   │   ├── stt/
│   │   │   ├── base.py      # STTService abstraction
│   │   │   └── faster_whisper.py
│   │   └── tts/
│   │       ├── base.py      # TTSService abstraction
│   │       └── piper.py     # Piper implementation
│   │   └── voice/
│   │       └── pipeline.py  # STT → LLM → TTS orchestration
│   └── schemas/
│       ├── chat.py
│       ├── transcription.py
│       ├── tts.py
│       └── voice.py
├── models/piper/            # Piper voice models (download separately)
├── storage/tts/             # Generated WAV files
├── tests/
│   ├── test_health.py
│   ├── test_chat.py
│   ├── test_transcribe.py
│   ├── test_tts.py
│   └── test_voice.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Architecture

The chat API depends on a `ChatService`, which delegates to an `LLMService` interface. The transcribe API depends on an `STTService` interface. The TTS API depends on a `TTSService` interface. The voice API uses `VoicePipelineService` to orchestrate all three without duplicating logic.

## Next phases

Future work will add telephony (Asterisk/SIP), streaming, and RAG. The full local voice loop is already available through **POST /voice**.
