# FootOps Agent Service

FastAPI service for evidence-checked football analysis. Local development
defaults to a transparent mock model mode; public match data and configured
knowledge retrieval remain available.

Rule and tactical-knowledge questions use the versioned Knowledge RAG corpus.
The local RAG path uses Redis 8 Vector Sets with deterministic hashed character
vectors, then combines vector similarity with BM25 and character matching. It
does not require Ollama or a downloaded embedding model. Data-plus-knowledge analysis
can compare two or more matches for one player and returns reviewed observations
with tactical concepts as references; it does not claim tactical causality.

```bash
source .venv/bin/activate
pip install -e 'services/agent[test]'
uvicorn footops_agent.api.main:app --app-dir services/agent/src --port 8000
```

Copy values from `.env.example` into the root `.env`. To use DeepSeek, set
`LLM_MODE=deepseek` and provide `DEEPSEEK_API_KEY`.

Redis stores only the versioned football-knowledge vectors. StatsBomb match
events and calculated metrics stay in the data/workspace path.

Run the Phase 2B golden-task comparison with:

```bash
.venv/bin/python -m footops_agent.cli.evaluate
```

Use `--modes deterministic` for a credential-free data-chain smoke test. The
full command compares deterministic direct execution, a tool-free direct LLM,
and the current AgentScope single Agent. Reports are written under
`data/evaluation/reports/`.
