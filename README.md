# FootOps

FootOps is a football research workspace for tactical learners and content
creators. Its Phase 2A golden path turns public match events into deterministic
metrics, reviewed findings, evidence, and an editable tactics-board artifact.

## Repository layout

```text
apps/web/                 React analysis workspace
services/agent/           Python FastAPI/AgentScope service
contracts/                HTTP and event contracts shared by services
docs/                     Product and architecture notes
infra/                    Future local and deployment infrastructure
```

Start with [`docs/FOOTOPS_AGENT_BASELINE.md`](docs/FOOTOPS_AGENT_BASELINE.md).
The baseline links to the separate product requirements, MindBridge-derived
architecture, and development-order documents.

## Run locally

```bash
npm install
.venv/bin/pip install -e 'services/agent[test]'
```

Start the API and web app in separate terminals:

```bash
.venv/bin/uvicorn footops_agent.api.main:app --host 127.0.0.1 --port 8000
npm run dev
```

The initial screen is intentionally blank. Submit a question to create a real
StatsBomb Open Data workspace over SSE. Phase 2A does not require an LLM key;
DeepSeek is only used by the separate planning spike when `LLM_MODE=deepseek`.
