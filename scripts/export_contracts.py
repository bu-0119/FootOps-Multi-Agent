"""Export versioned JSON Schema and OpenAPI documents from source models."""

from __future__ import annotations

import json
from pathlib import Path

from footops_agent.api.main import create_app
from footops_agent.api.schemas import (
    AgentRunStreamEvent,
    AnalysisStreamEvent,
    MultiAgentStreamEvent,
)
from footops_agent.artifacts import (
    AgentDecision,
    AgentModelUsage,
    AnalysisPlan,
    AnalysisWorkspace,
    CoverageAuditArtifact,
    EvidenceReference,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    ExecutionPlanArtifact,
    FindingSetArtifact,
    KnowledgeAnswerArtifact,
    KnowledgeEvidenceArtifact,
    MatchDataSnapshot,
    PlayerCatalogEntry,
    PlayerRoleMetricArtifact,
    ScopeResolutionArtifact,
    TacticalHypothesisArtifact,
    TacticsBoardArtifact,
)
from footops_agent.config import Settings

ROOT = Path(__file__).resolve().parents[1]

ARTIFACT_SCHEMAS = {
    "agent-decision.schema.json": AgentDecision,
    "agent-model-usage.schema.json": AgentModelUsage,
    "analysis-plan.schema.json": AnalysisPlan,
    "analysis-workspace.schema.json": AnalysisWorkspace,
    "coverage-audit.schema.json": CoverageAuditArtifact,
    "evidence-reference.schema.json": EvidenceReference,
    "evidence-review.schema.json": EvidenceReviewArtifact,
    "evidence-set.schema.json": EvidenceSetArtifact,
    "execution-plan.schema.json": ExecutionPlanArtifact,
    "finding-set.schema.json": FindingSetArtifact,
    "knowledge-answer.schema.json": KnowledgeAnswerArtifact,
    "knowledge-evidence.schema.json": KnowledgeEvidenceArtifact,
    "match-data-snapshot.schema.json": MatchDataSnapshot,
    "player-catalog-entry.schema.json": PlayerCatalogEntry,
    "player-role-metrics.schema.json": PlayerRoleMetricArtifact,
    "scope-resolution.schema.json": ScopeResolutionArtifact,
    "tactical-hypothesis.schema.json": TacticalHypothesisArtifact,
    "tactics-board.schema.json": TacticsBoardArtifact,
}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    artifact_dir = ROOT / "contracts/artifacts"
    for filename, model in ARTIFACT_SCHEMAS.items():
        write_json(artifact_dir / filename, model.model_json_schema())

    write_json(
        ROOT / "contracts/events/analysis-stream-event.schema.json",
        AnalysisStreamEvent.model_json_schema(),
    )
    write_json(
        ROOT / "contracts/events/agent-run-stream-event.schema.json",
        AgentRunStreamEvent.model_json_schema(),
    )
    write_json(
        ROOT / "contracts/events/multi-agent-stream-event.schema.json",
        MultiAgentStreamEvent.model_json_schema(),
    )

    app = create_app(settings=Settings(_env_file=None, llm_mode="mock"))
    write_json(
        ROOT / "contracts/openapi/footops-agent.openapi.json",
        app.openapi(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
