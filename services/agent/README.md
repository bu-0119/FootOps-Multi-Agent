# FootOps Agent Service

FastAPI service for structured football-analysis planning. Local development
defaults to a transparent mock mode that does not call an LLM or retrieve data.

```bash
source .venv/bin/activate
pip install -e 'services/agent[test]'
uvicorn footops_agent.api.main:app --app-dir services/agent/src --port 8000
```

Copy values from `.env.example` into the root `.env`. To use DeepSeek, set
`LLM_MODE=deepseek` and provide `DEEPSEEK_API_KEY`.
