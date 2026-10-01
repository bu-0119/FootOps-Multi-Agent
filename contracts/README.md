# Contracts

This directory contains generated OpenAPI documents and JSON Schemas shared by
the React frontend and Python agent service. Source Pydantic models remain the
authority; regenerate checked-in contracts with:

```bash
.venv/bin/python scripts/export_contracts.py
```

The initial endpoints are expected to be:

- `GET /health`
- `GET /api/v1/llm/status`
- `GET /api/v1/catalog/competitions`
- `GET /api/v1/catalog/players`
- `POST /api/v1/agent/runs`
- `POST /api/v1/agent/runs/stream`
- `POST /api/v1/multi-agent/runs`
- `POST /api/v1/multi-agent/analyses`
- `POST /api/v1/analyses/plan`
- `POST /api/v1/analyses`
- `POST /api/v1/analyses/stream`
- `GET /api/v1/analyses/{workspace_id}`
- `POST /api/v1/data/coverage-audit`
- `POST /api/v1/metrics/player-role`
- `POST /api/v1/findings/player-role/review`

`contracts/events/analysis-stream-event.schema.json` defines the versioned
`analysis.status`, `analysis.completed`, and `analysis.error` SSE payload. The
stream carries business lifecycle events; it is not a token-stream contract.
`contracts/events/agent-run-stream-event.schema.json` defines the Agent
started, tool, completion, clarification, unsupported, and error events.
`contracts/artifacts/agent-decision.schema.json` defines the structured
completion, clarification, and unsupported decisions returned by the Agent.
`contracts/artifacts/agent-model-usage.schema.json` defines provider-reported
Token counts and an optional operator-configured cost estimate.
`contracts/artifacts/scope-resolution.schema.json` defines the catalog-grounded
scope passed from ScopeAgent to the multi-agent collaboration runtime.
`contracts/artifacts/execution-plan.schema.json` declares independent match-data,
rule-RAG, tactical-RAG, multi-agent, and scope requirements before execution.
`contracts/artifacts/knowledge-evidence.schema.json` defines versioned retrieval
evidence, source provenance, and component scores. `knowledge-answer.schema.json`
defines the KnowledgeAgent answer and machine-checkable citation IDs.

The authoritative product, architecture, and implementation baselines are:

- [`docs/FOOTOPS_REQUIREMENTS.md`](../docs/FOOTOPS_REQUIREMENTS.md)
- [`docs/FOOTOPS_MINDBRIDGE_ARCHITECTURE.md`](../docs/FOOTOPS_MINDBRIDGE_ARCHITECTURE.md)
- [`docs/FOOTOPS_PROJECT_STRUCTURE_STANDARD.md`](../docs/FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)
- [`docs/FOOTOPS_DEVELOPMENT_ORDER.md`](../docs/FOOTOPS_DEVELOPMENT_ORDER.md)
