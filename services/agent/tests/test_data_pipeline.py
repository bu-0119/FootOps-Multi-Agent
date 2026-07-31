"""Deterministic coverage, normalization, metric, and API tests."""

from typing import Any

from fastapi.testclient import TestClient

from footops_agent.api.main import create_app
from footops_agent.artifacts import EvidenceSetArtifact, FindingSetArtifact
from footops_agent.config import Settings
from footops_agent.providers.statsbomb_open import StatsBombOpenDataProvider
from footops_agent.services import (
    DataCatalogService,
    DeterministicFindingBuilder,
    EvidenceGate,
    PlayerRoleAnalysisService,
)


class StubResourceClient:
    def __init__(self, resources: dict[str, Any]):
        self.resources = resources

    def url_for(self, relative_path: str) -> str:
        return f"https://example.test/data/{relative_path}"

    def fetch_json(self, relative_path: str) -> Any:
        return self.resources[relative_path]


def settings() -> Settings:
    return Settings(_env_file=None, llm_mode="mock")


def provider() -> StatsBombOpenDataProvider:
    resources: dict[str, Any] = {
        "competitions.json": [
            {
                "competition_id": 11,
                "season_id": 90,
                "country_name": "Spain",
                "competition_name": "La Liga",
                "season_name": "2020/2021",
            }
        ],
        "matches/11/90.json": [
            _match(1001, "2021-01-01"),
            _match(1002, "2021-01-08"),
            _match(1003, "2021-01-15"),
        ],
    }
    for match_id in (1001, 1002, 1003):
        resources[f"lineups/{match_id}.json"] = [_lineup()]
        resources[f"events/{match_id}.json"] = _events(match_id)
    return StatsBombOpenDataProvider(
        settings(),
        resource_client=StubResourceClient(resources),  # type: ignore[arg-type]
    )


def _match(match_id: int, match_date: str) -> dict[str, Any]:
    return {
        "match_id": match_id,
        "match_date": match_date,
        "competition": {
            "competition_id": 11,
            "country_name": "Spain",
            "competition_name": "La Liga",
        },
        "season": {"season_id": 90, "season_name": "2020/2021"},
        "home_team": {"home_team_id": 1, "home_team_name": "Barcelona"},
        "away_team": {"away_team_id": 2, "away_team_name": "Opponent"},
        "home_score": 2,
        "away_score": 1,
    }


def _lineup() -> dict[str, Any]:
    return {
        "team_id": 1,
        "team_name": "Barcelona",
        "lineup": [
            {
                "player_id": 30486,
                "player_name": "Pedro González López",
                "player_nickname": "Pedri",
                "positions": [
                    {
                        "position_id": 13,
                        "position": "Right Center Midfield",
                        "from": "00:00",
                        "to": "90:00",
                        "from_period": 1,
                        "to_period": 2,
                    }
                ],
            }
        ],
    }


def _event(
    match_id: int,
    index: int,
    event_type: str,
    location: list[float],
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": f"{match_id}-{index}",
        "index": index,
        "period": 1,
        "minute": index,
        "second": 0,
        "type": {"id": index, "name": event_type},
        "player": {"id": 30486, "name": "Pedro González López"},
        "location": location,
        "play_pattern": {"id": 1, "name": "Regular Play"},
    }
    if detail is not None:
        row[event_type.lower().replace("*", "").replace(" ", "_")] = detail
    return row


def _events(match_id: int) -> list[dict[str, Any]]:
    return [
        _event(
            match_id,
            1,
            "Ball Receipt*",
            [84, 30],
            {"outcome": {"id": 9, "name": "Incomplete"}},
        ),
        _event(
            match_id,
            2,
            "Pass",
            [60, 40],
            {"end_location": [90, 42]},
        ),
        _event(
            match_id,
            3,
            "Carry",
            [70, 35],
            {"end_location": [82, 36]},
        ),
        _event(match_id, 4, "Shot", [108, 40], {"outcome": {"name": "Saved"}}),
        _event(
            match_id,
            5,
            "Pass",
            [83, 30],
            {
                "end_location": [100, 35],
                "assisted_shot_id": f"shot-{match_id}",
                "shot_assist": True,
            },
        ),
    ]


def test_coverage_audit_resolves_nickname_and_suggests_window() -> None:
    audit = DataCatalogService(provider()).audit_player(11, 90, "Pedri", 3)

    assert audit.meets_minimum is True
    assert audit.matches_scanned == 3
    assert audit.suggested_match_ids == [1001, 1002, 1003]
    assert audit.appearances[0].player.player_name == "Pedro González López"
    assert audit.appearances[0].events_url.endswith("events/1001.json")


def test_metric_engine_uses_normalized_events_not_model_output() -> None:
    audit, metrics = PlayerRoleAnalysisService(provider()).calculate(
        11,
        90,
        "Pedri",
        3,
    )

    assert audit.meets_minimum is True
    row = metrics.matches[0]
    assert row.touch_event_count == 5
    assert row.attacking_third_touch_count == 3
    assert row.penalty_area_touch_count == 1
    assert row.forward_pass_count == 2
    assert row.completed_forward_pass_count == 2
    assert row.progressive_carry_count == 1
    assert row.key_pass_count == 1
    assert row.shot_involvement_count == 2


def test_data_api_is_explicitly_non_model_and_non_conclusive() -> None:
    app = create_app(settings=settings(), data_provider=provider())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/metrics/player-role",
            json={
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["model_called"] is False
    assert body["data_retrieved"] is True
    assert body["real_conclusions_generated"] is False
    assert len(body["metrics"]["matches"]) == 3


def test_deterministic_findings_pass_evidence_gate() -> None:
    _, metrics = PlayerRoleAnalysisService(provider()).calculate(11, 90, "Pedri", 3)
    findings, evidence = DeterministicFindingBuilder().build(metrics)

    review = EvidenceGate().review(findings, evidence, metrics)

    assert len(findings.findings) == 3
    assert review.overall_status == "passed"
    assert review.support_rate == 1.0
    assert all(item.status == "supported" for item in review.reviews)


def test_evidence_gate_rejects_forged_metric_value() -> None:
    _, metrics = PlayerRoleAnalysisService(provider()).calculate(11, 90, "Pedri", 3)
    findings, evidence = DeterministicFindingBuilder().build(metrics)
    target = next(item for item in evidence.references if item.kind == "metric")
    forged = target.model_copy(update={"metric_value": float(target.metric_value) + 1})
    forged_evidence = EvidenceSetArtifact(
        references=[
            forged if item.evidence_id == target.evidence_id else item
            for item in evidence.references
        ]
    )

    review = EvidenceGate().review(findings, forged_evidence, metrics)

    assert review.overall_status == "partial"
    assert any(item.status == "rejected" for item in review.reviews)
    assert any(
        "数值不一致" in reason
        for item in review.reviews
        for reason in item.reasons
    )


def test_evidence_gate_requires_more_evidence_for_inference() -> None:
    _, metrics = PlayerRoleAnalysisService(provider()).calculate(11, 90, "Pedri", 3)
    findings, evidence = DeterministicFindingBuilder().build(metrics)
    inference = findings.findings[0].model_copy(update={"claim_type": "inference"})
    inference_set = FindingSetArtifact(findings=[inference])

    review = EvidenceGate().review(inference_set, evidence, metrics)

    assert review.overall_status == "partial"
    assert review.support_rate == 0
    assert review.reviews[0].status == "needs_more_evidence"


def test_finding_review_api_returns_audited_observations() -> None:
    app = create_app(settings=settings(), data_provider=provider())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/findings/player-role/review",
            json={
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["model_called"] is False
    assert body["findings_generated"] is True
    assert body["evidence_reviewed"] is True
    assert body["real_conclusions_generated"] is False
    assert body["evidence_review"]["overall_status"] == "passed"
