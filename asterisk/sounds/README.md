# Custom Asterisk sounds

Extension **1001** uses these files from `custom/`:

| File | Purpose |
|------|---------|
| `ai-greeting.gsm` | Spoken greeting at call start |
| `beep.gsm` | Clear tone before each recording |
| `thinking.gsm` | "One moment please, I'm thinking." |
| `thinking-hold.gsm` | Short hold tone loop while Ollama responds |

Generate or refresh after changing `VOICE_GREETING` or `VOICE_THINKING_PROMPT` in `.env`:

```bash
docker compose exec voice-ai-backend uv run python scripts/generate_phone_sounds.py
docker compose exec asterisk asterisk -rx "dialplan reload"
```

Or use the legacy wrapper:

```bash
docker compose exec voice-ai-backend uv run python scripts/generate_greeting.py
```
