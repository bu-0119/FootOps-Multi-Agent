"""Read-only adapter for the public StatsBomb Open Data JSON repository."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from footops_agent.artifacts import (
    CompetitionSeason,
    MatchDataSnapshot,
    MatchRef,
    PitchLocation,
    PlayerEvent,
    PlayerMatchCoverage,
    PlayerRef,
    PositionInterval,
    SourceReference,
    TeamRef,
)
from footops_agent.config import Settings

from .base import DataProviderError, ResourceNotFoundError

JsonValue = dict[str, Any] | list[Any]

STATSBOMB_ATTRIBUTION = "StatsBomb Open Data"
STATSBOMB_LICENSE_URL = "https://github.com/hudl/open-data/blob/master/LICENSE.pdf"


class JsonResourceClient:
    """Fetch JSON resources with a local, Git-ignored file cache."""

    def __init__(self, base_url: str, cache_dir: Path, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds

    def url_for(self, relative_path: str) -> str:
        relative = self._safe_relative_path(relative_path)
        return f"{self.base_url}/{relative.as_posix()}"

    def fetch_json(self, relative_path: str) -> JsonValue:
        cache_path = self.cache_path_for(relative_path)
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cache_path.unlink(missing_ok=True)

        url = self.url_for(relative_path)
        try:
            response = httpx.get(
                url,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            raise DataProviderError(
                f"StatsBomb Open Data request failed: {url}"
            ) from exc
        if response.status_code == 404:
            raise ResourceNotFoundError(
                f"StatsBomb Open Data resource not found: {url}"
            )
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DataProviderError(
                f"Invalid StatsBomb Open Data response: {url}"
            ) from exc

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary.replace(cache_path)
        return payload

    def cache_path_for(self, relative_path: str) -> Path:
        relative = self._safe_relative_path(relative_path)
        return self.cache_dir.joinpath(*relative.parts)

    def retrieved_at_for(self, relative_path: str) -> datetime:
        cache_path = self.cache_path_for(relative_path)
        if cache_path.exists():
            return datetime.fromtimestamp(cache_path.stat().st_mtime, tz=UTC)
        return datetime.now(UTC)

    @staticmethod
    def _safe_relative_path(relative_path: str) -> PurePosixPath:
        relative = PurePosixPath(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("relative provider path must stay inside the data root")
        return relative


class StatsBombOpenDataProvider:
    """Normalize competitions, lineups, matches, and events from open data."""

    name = "statsbomb-open-data"

    def __init__(
        self,
        settings: Settings,
        resource_client: JsonResourceClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = resource_client or JsonResourceClient(
            settings.statsbomb_open_data_base_url,
            settings.footops_data_cache_dir,
            settings.footops_data_timeout_seconds,
        )

    def source_reference(self, relative_path: str) -> SourceReference:
        retrieved_at_for = getattr(self.client, "retrieved_at_for", None)
        retrieved_at = (
            retrieved_at_for(relative_path)
            if callable(retrieved_at_for)
            else datetime.now(UTC)
        )
        return SourceReference(
            provider=self.name,
            dataset="StatsBomb Open Data",
            source_url=self.client.url_for(relative_path),
            retrieved_at=retrieved_at,
            attribution=STATSBOMB_ATTRIBUTION,
            license_url=STATSBOMB_LICENSE_URL,
        )

    def list_competitions(self) -> list[CompetitionSeason]:
        rows = _expect_list(self.client.fetch_json("competitions.json"))
        competitions = [self._competition(row) for row in rows]
        return sorted(
            competitions,
            key=lambda item: (
                item.country_name,
                item.competition_name,
                item.season_name,
            ),
        )

    def list_matches(self, competition_id: int, season_id: int) -> list[MatchRef]:
        path = f"matches/{competition_id}/{season_id}.json"
        rows = _expect_list(self.client.fetch_json(path))
        return sorted(
            (self._match(row) for row in rows),
            key=lambda item: item.match_date,
        )

    def find_player_appearances(
        self,
        matches: list[MatchRef],
        player_query: str,
    ) -> list[PlayerMatchCoverage]:
        query = _normalize_name(player_query)
        if not query:
            raise ValueError("player query must not be blank")

        appearances = []
        for match in sorted(matches, key=lambda item: item.match_date):
            lineups_path = f"lineups/{match.match_id}.json"
            lineups = _expect_list(self.client.fetch_json(lineups_path))
            resolved = self._resolve_player(lineups, query)
            if resolved is None:
                continue
            player, team, positions = resolved
            if not positions:
                continue
            appearances.append(
                PlayerMatchCoverage(
                    match=match,
                    player=player,
                    team=team,
                    positions=positions,
                    lineups_url=self.client.url_for(lineups_path),
                    events_url=self.client.url_for(f"events/{match.match_id}.json"),
                )
            )
        return appearances

    def load_player_snapshot(
        self,
        coverage: PlayerMatchCoverage,
    ) -> MatchDataSnapshot:
        path = f"events/{coverage.match.match_id}.json"
        rows = _expect_list(self.client.fetch_json(path))
        events = []
        for row in rows:
            player = _mapping(row.get("player"))
            if _optional_int(player.get("id")) != coverage.player.player_id:
                continue
            events.append(self._player_event(coverage.match.match_id, row))
        return MatchDataSnapshot(
            source=self.source_reference(path),
            match=coverage.match,
            player=coverage.player,
            team=coverage.team,
            positions=coverage.positions,
            events=events,
        )

    def _competition(self, row: Mapping[str, Any]) -> CompetitionSeason:
        return CompetitionSeason(
            competition_id=_required_int(row, "competition_id"),
            season_id=_required_int(row, "season_id"),
            country_name=_required_str(row, "country_name"),
            competition_name=_required_str(row, "competition_name"),
            season_name=_required_str(row, "season_name"),
        )

    def _match(self, row: Mapping[str, Any]) -> MatchRef:
        competition = _mapping(row.get("competition"))
        season = _mapping(row.get("season"))
        home_team = _mapping(row.get("home_team"))
        away_team = _mapping(row.get("away_team"))
        return MatchRef(
            match_id=_required_int(row, "match_id"),
            match_date=date.fromisoformat(_required_str(row, "match_date")),
            competition=CompetitionSeason(
                competition_id=_required_int(competition, "competition_id"),
                season_id=_required_int(season, "season_id"),
                country_name=_required_str(competition, "country_name"),
                competition_name=_required_str(competition, "competition_name"),
                season_name=_required_str(season, "season_name"),
            ),
            home_team=TeamRef(
                team_id=_required_int(home_team, "home_team_id"),
                team_name=_required_str(home_team, "home_team_name"),
            ),
            away_team=TeamRef(
                team_id=_required_int(away_team, "away_team_id"),
                team_name=_required_str(away_team, "away_team_name"),
            ),
            home_score=_optional_int(row.get("home_score")),
            away_score=_optional_int(row.get("away_score")),
        )

    def _resolve_player(
        self,
        lineups: list[Any],
        query: str,
    ) -> tuple[PlayerRef, TeamRef, list[PositionInterval]] | None:
        candidates = []
        for team_row in lineups:
            team_data = _mapping(team_row)
            team = TeamRef(
                team_id=_required_int(team_data, "team_id"),
                team_name=_required_str(team_data, "team_name"),
            )
            for player_row in _expect_list(team_data.get("lineup", [])):
                player_data = _mapping(player_row)
                full_name = _required_str(player_data, "player_name")
                nickname = _optional_str(player_data.get("player_nickname"))
                score = _name_match_score(query, full_name, nickname)
                if score == 0:
                    continue
                positions = [
                    self._position(_mapping(position))
                    for position in _expect_list(player_data.get("positions", []))
                ]
                candidates.append(
                    (
                        score,
                        PlayerRef(
                            player_id=_required_int(player_data, "player_id"),
                            player_name=full_name,
                            player_nickname=nickname,
                        ),
                        team,
                        positions,
                    )
                )
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        best = candidates[0]
        if len(candidates) > 1 and candidates[1][0] == best[0]:
            if candidates[1][1].player_id != best[1].player_id:
                raise DataProviderError("player query is ambiguous in lineup data")
        return best[1], best[2], best[3]

    def _position(self, row: Mapping[str, Any]) -> PositionInterval:
        return PositionInterval(
            position_id=_required_int(row, "position_id"),
            position_name=_required_str(row, "position"),
            from_time=_optional_str(row.get("from")),
            to_time=_optional_str(row.get("to")),
            from_period=_optional_int(row.get("from_period")),
            to_period=_optional_int(row.get("to_period")),
        )

    def _player_event(self, match_id: int, row: Mapping[str, Any]) -> PlayerEvent:
        event_type = _mapping(row.get("type"))
        event_name = _required_str(event_type, "name")
        detail_key = event_name.lower().replace("*", "").replace(" ", "_")
        detail = _mapping(row.get(detail_key))
        pass_detail = _mapping(row.get("pass"))
        end_location = detail.get("end_location")
        outcome = _mapping(detail.get("outcome"))
        play_pattern = _mapping(row.get("play_pattern"))
        return PlayerEvent(
            event_id=_required_str(row, "id"),
            event_index=_required_int(row, "index"),
            match_id=match_id,
            period=_required_int(row, "period"),
            minute=_required_int(row, "minute"),
            second=_required_int(row, "second"),
            event_type=event_name,
            event_type_id=_required_int(event_type, "id"),
            play_pattern=_optional_str(play_pattern.get("name")),
            location=_location(row.get("location")),
            end_location=_location(end_location),
            outcome=_optional_str(outcome.get("name")),
            pass_assisted_shot_id=_optional_str(pass_detail.get("assisted_shot_id")),
            pass_shot_assist=bool(pass_detail.get("shot_assist", False)),
            pass_goal_assist=bool(pass_detail.get("goal_assist", False)),
        )


def _expect_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise DataProviderError("expected a JSON array from football-data provider")
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _required_int(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataProviderError(f"required integer field is missing: {key}")
    return value


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _required_str(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DataProviderError(f"required string field is missing: {key}")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _location(value: Any) -> PitchLocation | None:
    if not isinstance(value, list) or len(value) < 2:
        return None
    x, y = value[0], value[1]
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        return None
    return PitchLocation(x=float(x), y=float(y))


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(ascii_text.casefold().split())


def _name_match_score(query: str, full_name: str, nickname: str | None) -> int:
    full = _normalize_name(full_name)
    nick = _normalize_name(nickname or "")
    if query == nick:
        return 4
    if query == full:
        return 3
    if nick and query in nick:
        return 2
    if query in full:
        return 1
    return 0
