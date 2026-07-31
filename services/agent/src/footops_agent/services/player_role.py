"""Vertical data-to-metrics use case for the player-role golden task."""

from footops_agent.artifacts import CoverageAuditArtifact, PlayerRoleMetricArtifact
from footops_agent.providers import FootballDataProvider

from .data_catalog import DataCatalogService, InsufficientDataError
from .metric_engine import PlayerRoleMetricEngine


class PlayerRoleAnalysisService:
    """Load an audited match window and calculate deterministic metrics."""

    def __init__(
        self,
        provider: FootballDataProvider,
        metric_engine: PlayerRoleMetricEngine | None = None,
    ) -> None:
        self.provider = provider
        self.catalog = DataCatalogService(provider)
        self.metric_engine = metric_engine or PlayerRoleMetricEngine()

    def calculate(
        self,
        competition_id: int,
        season_id: int,
        player_query: str,
        requested_window: int = 5,
    ) -> tuple[CoverageAuditArtifact, PlayerRoleMetricArtifact]:
        audit = self.catalog.audit_player(
            competition_id,
            season_id,
            player_query,
            requested_window,
        )
        if not audit.meets_minimum:
            raise InsufficientDataError(
                "public event data does not contain the three-match minimum"
            )
        selected_ids = set(audit.suggested_match_ids)
        selected = [
            appearance
            for appearance in audit.appearances
            if appearance.match.match_id in selected_ids
        ]
        snapshots = [self.provider.load_player_snapshot(item) for item in selected]
        return audit, self.metric_engine.compute(snapshots)
