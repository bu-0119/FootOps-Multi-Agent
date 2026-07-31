export interface SourceReference {
  provider: string;
  dataset: string;
  source_url: string;
  retrieved_at: string;
  attribution: string;
  license_url: string;
}

export interface PlayerRef {
  player_id: number;
  player_name: string;
  player_nickname: string | null;
}

export interface CompetitionSeason {
  competition_id: number;
  season_id: number;
  country_name: string;
  competition_name: string;
  season_name: string;
}

export interface TeamRef {
  team_id: number;
  team_name: string;
}

export interface PositionInterval {
  position_id: number;
  position_name: string;
  from_time: string | null;
  to_time: string | null;
  from_period: number | null;
  to_period: number | null;
}

export interface MatchRef {
  match_id: number;
  match_date: string;
  competition: CompetitionSeason;
  home_team: TeamRef;
  away_team: TeamRef;
  home_score: number | null;
  away_score: number | null;
}

export interface PlayerMatchCoverage {
  match: MatchRef;
  player: PlayerRef;
  team: TeamRef;
  positions: PositionInterval[];
  lineups_url: string;
  events_url: string;
}

export interface MatchRoleMetrics {
  match_id: number;
  match_date: string;
  event_count: number;
  touch_event_count: number;
  average_touch_x: number | null;
  average_touch_y: number | null;
  attacking_third_touch_count: number;
  attacking_third_touch_ratio: number | null;
  penalty_area_touch_count: number;
  penalty_area_touch_ratio: number | null;
  receipt_count: number;
  average_receipt_x: number | null;
  forward_pass_count: number;
  completed_forward_pass_count: number;
  progressive_carry_count: number;
  key_pass_count: number;
  shot_count: number;
  shot_involvement_count: number;
}

export interface PlayerRoleMetricArtifact {
  schema_version: "1.0";
  metric_definition_version: "footops-player-role-v1";
  generated_at: string;
  player: PlayerRef;
  sources: SourceReference[];
  matches: MatchRoleMetrics[];
  limitations: string[];
}

export interface CoverageAuditArtifact {
  schema_version: "1.0";
  source: SourceReference;
  query: string;
  competition: CompetitionSeason;
  matches_scanned: number;
  requested_window: number;
  suggested_match_ids: number[];
  meets_minimum: boolean;
  warnings: string[];
  appearances: PlayerMatchCoverage[];
}

export interface PlayerRoleMetricsResponse {
  status: "calculated";
  provider: "statsbomb-open-data";
  model_called: false;
  data_retrieved: true;
  real_conclusions_generated: false;
  audit: CoverageAuditArtifact;
  metrics: PlayerRoleMetricArtifact;
}

export interface FindingTimeRange {
  start_date: string;
  end_date: string;
  match_ids: number[];
}

export interface FindingArtifact {
  schema_version: "1.0";
  finding_id: string;
  statement: string;
  claim_type: "descriptive" | "inference";
  metric_refs: string[];
  source_refs: string[];
  time_range: FindingTimeRange;
  direction: "increase" | "decrease" | "stable";
  confidence: number;
  limitations: string[];
}

export interface FindingSetArtifact {
  schema_version: "1.0";
  generated_at: string;
  generator: "footops-deterministic-finding-v1";
  findings: FindingArtifact[];
}

export interface EvidenceReference {
  evidence_id: string;
  kind: "source" | "metric";
  source_url: string | null;
  match_id: number | null;
  metric_name: string | null;
  metric_value: number | null;
  detail: string;
}

export interface FindingEvidenceReview {
  finding_id: string;
  status: "supported" | "needs_more_evidence" | "rejected";
  accepted_metric_refs: string[];
  accepted_source_refs: string[];
  reasons: string[];
}

export interface EvidenceReviewArtifact {
  schema_version: "1.0";
  reviewed_at: string;
  gate_version: "footops-evidence-gate-v1";
  overall_status: "passed" | "partial" | "rejected";
  support_rate: number;
  reviews: FindingEvidenceReview[];
  limitations: string[];
}

export interface EvidenceSetArtifact {
  schema_version: "1.0";
  generated_at: string;
  references: EvidenceReference[];
}

export interface BoardPoint {
  x: number;
  y: number;
}

export interface TacticsPlayerMarker {
  marker_id: string;
  label: string;
  display_label: string;
  position: BoardPoint;
  role: "focus" | "teammate" | "opponent";
  finding_refs: string[];
}

export interface TacticsZone {
  zone_id: string;
  label: string;
  kind: "touch_area" | "attacking_third";
  x: number;
  y: number;
  width: number;
  height: number;
  finding_refs: string[];
}

export interface TacticsArrow {
  arrow_id: string;
  label: string;
  kind: "movement" | "passing";
  start: BoardPoint;
  end: BoardPoint;
  finding_refs: string[];
}

export interface TacticsAnnotation {
  annotation_id: string;
  text: string;
  finding_refs: string[];
}

export interface TacticsBoardArtifact {
  schema_version: "1.0";
  generated_at: string;
  generator: "footops-deterministic-tactics-v1";
  title: string;
  pitch_orientation: "vertical_attacking_up";
  formation: "unassigned" | "4-3-3" | "4-2-3-1" | "3-4-3";
  players: TacticsPlayerMarker[];
  zones: TacticsZone[];
  arrows: TacticsArrow[];
  passing_lanes: TacticsArrow[];
  annotations: TacticsAnnotation[];
  finding_refs: string[];
  evidence_refs: string[];
  limitations: string[];
}

export interface AnalysisWorkspace {
  schema_version: "1.0";
  workspace_id: string;
  status:
    | "created"
    | "data_ready"
    | "metrics_ready"
    | "findings_ready"
    | "evidence_reviewed"
    | "tactics_ready"
    | "completed"
    | "insufficient_data"
    | "failed";
  request: {
    question: string;
    scope: {
      competition_id: number;
      season_id: number;
      player: string;
      team: string | null;
      match_ids: number[];
    };
  };
  coverage: CoverageAuditArtifact | null;
  metrics: PlayerRoleMetricArtifact | null;
  findings: FindingArtifact[];
  evidence: EvidenceSetArtifact | null;
  evidence_review: EvidenceReviewArtifact | null;
  tactics_board: TacticsBoardArtifact | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisWorkspaceResponse {
  status: "ready";
  provider: "statsbomb-open-data";
  model_called: false;
  data_retrieved: true;
  findings_generated: true;
  evidence_reviewed: true;
  tactics_board_generated: true;
  real_conclusions_generated: false;
  workspace: AnalysisWorkspace;
}

interface ErrorResponse {
  error?: { message?: string };
}

interface AnalysisStreamEvent {
  schema_version: "1.0";
  event: "analysis.status" | "analysis.completed" | "analysis.error";
  request_id: string;
  sequence: number;
  message: string;
  response: AnalysisWorkspaceResponse | null;
  error: { code: string; message: string } | null;
}

export async function requestPedriHistoricalMetrics(
  signal?: AbortSignal,
): Promise<PlayerRoleMetricsResponse> {
  const response = await fetch("/api/v1/metrics/player-role", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      competition_id: 11,
      season_id: 90,
      player: "Pedri",
      requested_window: 5,
    }),
    signal,
  });

  if (!response.ok) {
    let detail: ErrorResponse | undefined;
    try {
      detail = (await response.json()) as ErrorResponse;
    } catch {
      detail = undefined;
    }
    throw new Error(
      detail?.error?.message ?? "历史公开比赛数据暂时不可用。",
    );
  }

  return (await response.json()) as PlayerRoleMetricsResponse;
}

export async function createPlayerRoleWorkspace(
  question: string,
  signal?: AbortSignal,
  onStatus?: (message: string) => void,
): Promise<AnalysisWorkspaceResponse> {
  const response = await fetch("/api/v1/analyses/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      competition_id: 11,
      season_id: 90,
      player: "Pedri",
      requested_window: 5,
    }),
    signal,
  });

  if (!response.ok) {
    let detail: ErrorResponse | undefined;
    try {
      detail = (await response.json()) as ErrorResponse;
    } catch {
      detail = undefined;
    }
    throw new Error(
      detail?.error?.message ?? "描述性观察与证据审核暂时不可用。",
    );
  }

  if (!response.body) {
    throw new Error("浏览器无法读取分析事件流。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: AnalysisWorkspaceResponse | null = null;

  const consumeEvent = (rawEvent: string) => {
    const normalized = rawEvent.replaceAll("\r\n", "\n");
    const data = normalized
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) {
      return;
    }

    const event = JSON.parse(data) as AnalysisStreamEvent;
    if (event.event === "analysis.status") {
      onStatus?.(event.message);
      return;
    }
    if (event.event === "analysis.error") {
      throw new Error(event.error?.message ?? "分析事件流执行失败。");
    }
    if (event.event === "analysis.completed" && event.response) {
      completed = event.response;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() ?? "";
    events.forEach(consumeEvent);
    if (done) {
      break;
    }
  }
  if (buffer.trim()) {
    consumeEvent(buffer);
  }
  if (!completed) {
    throw new Error("分析事件流结束，但未返回工作区。");
  }
  return completed;
}
