import {
  AlertCircle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  FileText,
  LoaderCircle,
  Search,
  Swords,
  UserRoundSearch,
} from "lucide-react";
import type { AnalysisWorkspace } from "../api/data";

interface ViewActions {
  onOpenChat: () => void;
  onOpenBoard: () => void;
  onNotify: (message: string) => void;
  workspace: AnalysisWorkspace | null;
  metricsLoading: boolean;
  metricError: string;
}

function ViewHeading({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <header className="view-heading">
      <div className="view-heading-icon">{icon}</div>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </header>
  );
}

function DataState({ loading, error }: { loading: boolean; error: string }) {
  if (loading) {
    return (
      <div className="panel-empty">
        <LoaderCircle className="spin" size={22} />
        <strong>正在读取公开比赛数据</strong>
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel-empty error">
        <AlertCircle size={22} />
        <strong>数据暂时不可用</strong>
        <span>{error}</span>
      </div>
    );
  }
  return null;
}

export function MatchesView({
  onOpenChat,
  workspace,
  metricsLoading,
  metricError,
}: ViewActions) {
  const selectedIds = new Set(workspace?.coverage?.suggested_match_ids ?? []);
  const matches =
    workspace?.coverage?.appearances.filter((item) =>
      selectedIds.has(item.match.match_id),
    ) ?? [];
  const calculatedIds = new Set(
    workspace?.metrics?.matches.map((match) => match.match_id) ?? [],
  );

  return (
    <section className="research-view">
      <ViewHeading
        icon={<CalendarDays size={20} />}
        title="比赛研究"
        description="当前只展示已载入并参与黄金样例计算的真实历史比赛。"
      />
      <div className="view-toolbar">
        <label className="search-field">
          <Search size={17} />
          <span className="sr-only">搜索比赛</span>
          <input placeholder="搜索当前五场比赛" />
        </label>
      </div>
      <DataState loading={metricsLoading} error={metricError} />
      {!metricsLoading && !metricError && matches.length > 0 && (
        <div className="data-table match-table">
          <div className="data-table-head">
            <span>比赛</span>
            <span>日期</span>
            <span>赛事</span>
            <span>数据状态</span>
            <span className="sr-only">操作</span>
          </div>
          {matches.map(({ match }) => (
            <div className="data-table-row" key={match.match_id}>
              <div className="match-cell">
                <span className="team-monogram">{match.home_team.team_name.slice(0, 1)}</span>
                <div>
                  <strong>
                    {match.home_team.team_name}{" "}
                    <b>
                      {match.home_score != null && match.away_score != null
                        ? `${match.home_score}–${match.away_score}`
                        : "vs"}
                    </b>{" "}
                    {match.away_team.team_name}
                  </strong>
                  <span>StatsBomb Open Data</span>
                </div>
              </div>
              <span>{match.match_date}</span>
              <span>{match.competition.competition_name}</span>
              <div className="verified-data-state">
                <CheckCircle2 size={15} />
                <span>{calculatedIds.has(match.match_id) ? "指标已计算" : "事件已载入"}</span>
              </div>
              <button
                className="row-action"
                type="button"
                title="在问答中查看"
                aria-label={`查看 ${match.home_team.team_name} 对 ${match.away_team.team_name}`}
                onClick={onOpenChat}
              >
                <ArrowRight size={17} />
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function PlayersView({
  onOpenChat,
  workspace,
  metricsLoading,
  metricError,
}: ViewActions) {
  const response = workspace;
  const selectedIds = new Set(response?.coverage?.suggested_match_ids ?? []);
  const appearances =
    response?.coverage?.appearances.filter((item) =>
      selectedIds.has(item.match.match_id),
    ) ?? [];
  const positions = Array.from(
    new Set(appearances.flatMap((item) => item.positions.map((p) => p.position_name))),
  );
  const player = response?.metrics?.player;

  return (
    <section className="research-view">
      <ViewHeading
        icon={<UserRoundSearch size={20} />}
        title="球员研究"
        description="只展示当前数据集已完成确定性指标计算的球员。"
      />
      <DataState loading={metricsLoading} error={metricError} />
      {!metricsLoading && !metricError && player && (
        <div className="player-list">
          <article className="player-row">
            <div className="player-number">{(player.player_nickname ?? player.player_name).slice(0, 1)}</div>
            <div className="player-identity">
              <strong>{player.player_nickname ?? player.player_name}</strong>
              <span>{appearances[0]?.team.team_name ?? "—"} · {positions.join("、") || "位置未记录"}</span>
            </div>
            <div className="player-focus">
              <span>当前状态</span>
              <strong>指标已计算，战术结论待审核</strong>
            </div>
            <div className="player-sample">
              <span>样本</span>
              <strong>{response.metrics?.matches.length ?? 0} 场</strong>
            </div>
            <button
              className="row-action"
              type="button"
              title="查看指标"
              aria-label={`查看 ${player.player_nickname ?? player.player_name} 指标`}
              onClick={onOpenChat}
            >
              <ArrowRight size={17} />
            </button>
          </article>
        </div>
      )}
    </section>
  );
}

export function TacticsLibraryView({
  workspace,
  onOpenBoard,
}: {
  workspace: AnalysisWorkspace | null;
  onOpenBoard: () => void;
}) {
  const artifact = workspace?.tactics_board;
  const player = artifact?.players[0];
  const arrow = artifact?.arrows[0];
  return (
    <section className="research-view">
      <ViewHeading
        icon={<Swords size={20} />}
        title="战术板"
        description="这里只保存经过审核并由 TacticsBoardArtifact 生成的战术板。"
      />
      {artifact ? (
        <div className="board-library">
          <article className="board-library-item">
            <div className="mini-pitch">
              {artifact.zones.map((zone) => (
                <span
                  className="mini-artifact-zone"
                  key={zone.zone_id}
                  style={{
                    left: `${zone.x}%`,
                    top: `${zone.y}%`,
                    width: `${zone.width}%`,
                    height: `${zone.height}%`,
                  }}
                />
              ))}
              {arrow && (
                <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                  <line
                    x1={arrow.start.x}
                    y1={arrow.start.y}
                    x2={arrow.end.x}
                    y2={arrow.end.y}
                  />
                </svg>
              )}
              {player && (
                <i
                  style={{
                    left: `${player.position.x}%`,
                    top: `${player.position.y}%`,
                  }}
                />
              )}
            </div>
            <div>
              <strong>{artifact.title}</strong>
              <span>未指定阵型 · 样本位置变化图</span>
              <small>
                {artifact.finding_refs.length} 条 Finding · {artifact.evidence_refs.length} 个证据引用
              </small>
            </div>
            <button type="button" onClick={onOpenBoard}>
              打开战术板
              <ArrowRight size={15} />
            </button>
          </article>
        </div>
      ) : (
        <div className="panel-empty">
          <Swords size={24} />
          <strong>尚无已生成的战术板</strong>
          <span>提交分析问题并通过证据审核后，这里会出现结构化战术板。</span>
        </div>
      )}
    </section>
  );
}

export function ReportsView() {
  return (
    <section className="research-view">
      <ViewHeading
        icon={<FileText size={20} />}
        title="报告"
        description="这里只展示经过证据审核并已持久化的分析报告。"
      />
      <div className="panel-empty">
        <FileText size={24} />
        <strong>尚无真实分析报告</strong>
        <span>五场指标和证据审核已经保存，报告生成仍在开发中。</span>
      </div>
    </section>
  );
}
