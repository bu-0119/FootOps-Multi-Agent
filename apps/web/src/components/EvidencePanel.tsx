import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Database,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import type { AnalysisWorkspace } from "../api/data";

interface EvidencePanelProps {
  workspace: AnalysisWorkspace | null;
  loading: boolean;
  error: string;
}

export function EvidencePanel({
  workspace,
  loading,
  error,
}: EvidencePanelProps) {
  const audit = workspace?.coverage;
  const metrics = workspace?.metrics;
  const selectedIds = new Set(audit?.suggested_match_ids ?? []);
  const selectedAppearances =
    audit?.appearances.filter((item) => selectedIds.has(item.match.match_id)) ?? [];
  const positions = Array.from(
    new Set(selectedAppearances.flatMap((item) => item.positions.map((p) => p.position_name))),
  );
  const review = workspace?.evidence_review;

  return (
    <div className="evidence-panel-content">
      <div
        className={`evidence-summary ${review?.overall_status === "passed" ? "" : "pending"}`}
      >
        <div>
          <ShieldCheck size={20} />
          <span>证据审核状态</span>
        </div>
        <strong>
          {loading
            ? "载入中"
            : error
              ? "不可用"
              : `${Math.round((review?.support_rate ?? 0) * 100)}%`}
        </strong>
        <p>
          {error
            ? error
            : "描述性 Finding 的指标值、比赛范围和来源引用已完成确定性核验。"}
        </p>
      </div>

      {workspace && (
        <section className="evidence-section">
          <div className="right-section-heading">
            <ShieldCheck size={17} />
            <h3>Finding 审核</h3>
          </div>
          <div className="finding-review-list">
            {workspace.findings.map((finding) => {
              const findingReview = review?.reviews.find(
                (item) => item.finding_id === finding.finding_id,
              );
              return (
                <article key={finding.finding_id}>
                  <CheckCircle2 size={16} />
                  <div>
                    <strong>{finding.statement}</strong>
                    <span>
                      {findingReview?.accepted_metric_refs.length ?? 0} 个指标引用 ·{" "}
                      {findingReview?.accepted_source_refs.length ?? 0} 个来源引用
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="evidence-section">
        <div className="right-section-heading">
          <Database size={17} />
          <h3>实际数据来源</h3>
        </div>
        {metrics ? (
          <div className="source-list">
            {metrics.sources.map((source, index) => (
              <article className="source-item" key={source.source_url}>
                <div className="source-index">{index + 1}</div>
                <div className="source-copy">
                  <div className="source-name-row">
                    <strong>{source.dataset}</strong>
                    <a
                      className="icon-button quiet"
                      href={source.source_url}
                      target="_blank"
                      rel="noreferrer"
                      title="打开来源"
                      aria-label={`打开 ${source.dataset}`}
                    >
                      <ExternalLink size={15} />
                    </a>
                  </div>
                  <span>{source.attribution}</span>
                  <p>第 {index + 1} 场比赛事件文件；指标由 FootOps 确定性代码计算。</p>
                  <div className="source-meta">
                    <span>事件文件 {index + 1} / {metrics.sources.length}</span>
                    <span>{source.provider}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="panel-empty compact">
            <Database size={20} />
            <strong>{loading ? "正在读取数据来源" : "暂无可用来源"}</strong>
          </div>
        )}
      </section>

      <section className="evidence-section">
        <div className="right-section-heading">
          <CalendarClock size={17} />
          <h3>实际分析范围</h3>
        </div>
        <dl className="scope-list">
          <div>
            <dt>赛事</dt>
            <dd>{audit ? `${audit.competition.competition_name} ${audit.competition.season_name}` : "—"}</dd>
          </div>
          <div>
            <dt>样本</dt>
            <dd>{metrics ? `${metrics.matches.length} 场` : "—"}</dd>
          </div>
          <div>
            <dt>球员</dt>
            <dd>{metrics?.player.player_nickname ?? metrics?.player.player_name ?? "—"}</dd>
          </div>
          <div>
            <dt>阵容位置</dt>
            <dd>{positions.length > 0 ? positions.join("、") : "—"}</dd>
          </div>
        </dl>
      </section>

      <div className="evidence-note">
        <AlertCircle size={15} />
        当前指标不包含跟踪数据，也不代表已经形成战术结论。
      </div>
    </div>
  );
}
