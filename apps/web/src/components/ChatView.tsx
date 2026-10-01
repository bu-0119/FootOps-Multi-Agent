import { FormEvent, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Download,
  FileText,
  Link2,
  MessageCircleMore,
  Paperclip,
  ScanSearch,
  Send,
  SlidersHorizontal,
  Swords,
} from "lucide-react";
import {
  type AnalysisWorkspace,
  type CompetitionSeason,
  type KnowledgeAnswerArtifact,
  type KnowledgeEvidenceArtifact,
  type PlayerCatalogEntry,
} from "../api/data";
import { TrendChart } from "./TrendChart";

interface ChatViewProps {
  onShowTactics: () => void;
  onShowEvidence: () => void;
  onNotify: (message: string) => void;
  onAnalyze: (question: string) => Promise<void>;
  workspace: AnalysisWorkspace | null;
  pendingQuestion: string;
  metricsLoading: boolean;
  metricError: string;
  agentStatus:
    | "chat"
    | "completed"
    | "clarification_required"
    | "unsupported"
    | null;
  agentMessage: string;
  isHybridAnalysis: boolean;
  knowledgeEvidence: KnowledgeEvidenceArtifact | null;
  knowledgeAnswer: KnowledgeAnswerArtifact | null;
  agentActivity: string;
  competitions: CompetitionSeason[];
  selectedCompetition: CompetitionSeason | null;
  onSelectCompetition: (value: string) => void;
  players: PlayerCatalogEntry[];
  playerQuery: string;
  onPlayerQueryChange: (value: string) => void;
  requestedWindow: number | undefined;
  onRequestedWindowChange: (value: number | undefined) => void;
  catalogLoading: boolean;
  catalogError: string;
}

export function ChatView({
  onShowTactics,
  onShowEvidence,
  onNotify,
  onAnalyze,
  workspace,
  pendingQuestion,
  metricsLoading,
  metricError,
  agentStatus,
  agentMessage,
  isHybridAnalysis,
  knowledgeEvidence,
  knowledgeAnswer,
  agentActivity,
  competitions,
  selectedCompetition,
  onSelectCompetition,
  players,
  playerQuery,
  onPlayerQueryChange,
  requestedWindow,
  onRequestedWindowChange,
  catalogLoading,
  catalogError,
}: ChatViewProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const [scopeOpen, setScopeOpen] = useState(false);
  const [typedAgentMessage, setTypedAgentMessage] = useState("");
  const metricRows = workspace?.metrics?.matches ?? [];
  const findings = workspace?.findings ?? [];
  const evidenceReview = workspace?.evidence_review;
  const isKnowledgeAnswer = knowledgeAnswer?.status === "answered";
  const citedKnowledge = (knowledgeEvidence?.references ?? []).filter(
    (reference) => knowledgeAnswer?.citation_ids.includes(reference.evidence_id),
  );
  const displayTime = workspace?.metrics
    ? new Date(workspace.metrics.generated_at).toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "";
  const activeQuestion =
    workspace?.request.question || pendingQuestion || submittedQuestion;
  const hasAnalysis = Boolean(
    activeQuestion || workspace || metricsLoading || metricError || agentMessage,
  );
  const competitionLabel = selectedCompetition
    ? `${selectedCompetition.competition_name} ${selectedCompetition.season_name}`
    : "未选择赛事";
  const windowLabel = requestedWindow
    ? `近 ${requestedWindow} 场`
    : "窗口由 Agent 解析";
  const resolvedPlayer = players.find(
    (entry) =>
      entry.player.player_name.toLocaleLowerCase() ===
        playerQuery.trim().toLocaleLowerCase() ||
      entry.player.player_nickname?.toLocaleLowerCase() ===
        playerQuery.trim().toLocaleLowerCase(),
  );

  useEffect(() => {
    if (!agentMessage) {
      setTypedAgentMessage("");
      return;
    }
    setTypedAgentMessage("");
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setTypedAgentMessage(agentMessage.slice(0, index));
      if (index >= agentMessage.length) {
        window.clearInterval(timer);
      }
    }, 18);
    return () => window.clearInterval(timer);
  }, [agentMessage]);

  const submitQuestion = async (event: FormEvent) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || isSubmitting || metricsLoading) {
      return;
    }
    setSubmittedQuestion(question);
    setDraft("");
    setIsSubmitting(true);
    await onAnalyze(question);
    setIsSubmitting(false);
  };

  const exportAnswer = () => {
    const content = [
      "FootOps 历史公开比赛分析",
      "",
      `球员：${workspace?.metrics?.player.player_name ?? playerQuery}`,
      `赛事：${workspace?.coverage?.competition.competition_name ?? competitionLabel} ${workspace?.coverage?.competition.season_name ?? ""}`,
      `样本：${metricRows.length} 场`,
      "",
      ...findings.map((finding) => `- ${finding.statement}`),
      "",
      "以上是已通过确定性证据门禁的描述性观察，不构成战术因果结论。",
      "来源：StatsBomb Open Data",
    ].join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "footops-analysis.txt";
    link.click();
    URL.revokeObjectURL(url);
    onNotify("分析摘要已导出");
  };

  return (
    <section className="chat-view">
      <div className="conversation-scroll">
        {!hasAnalysis ? (
          <div className="analysis-empty-state">
            <ScanSearch size={28} />
            <h2>开始一项足球分析</h2>
            <p>直接描述你想研究的问题；赛事、球员和窗口都可以由 Agent 解析</p>
          </div>
        ) : (
          <>
            {activeQuestion && (
              <div className="user-message-row">
                <div className="user-message">{activeQuestion}</div>
                {displayTime && <time>{displayTime}</time>}
              </div>
            )}

            <article className="assistant-answer">
              <header className="assistant-header">
                <div className="assistant-avatar" aria-hidden="true">
                  <span />
                  <span />
                </div>
                <strong>FootOps</strong>
                {displayTime && <time>{displayTime}</time>}
              </header>

              {agentStatus === "chat" && !metricsLoading ? (
                <div className="chat-response-label">
                  <MessageCircleMore size={16} />
                  普通对话 · 未启动比赛分析
                </div>
              ) : (
                <button
                  className="verification-status"
                  type="button"
                  onClick={onShowEvidence}
                >
                <span>
                  <Link2 size={16} />
                  {metricsLoading
                    ? agentActivity || "正在处理"
                    : metricError
                      ? "当前问题未生成分析"
                      : isKnowledgeAnswer
                        ? `已检索 ${citedKnowledge.length} 条版本化规则证据`
                      : agentStatus === "clarification_required"
                        ? "需要补充分析范围"
                        : agentStatus === "unsupported"
                          ? "当前能力边界"
                      : `已审核 ${findings.length} 条描述性观察`}
                </span>
                <strong>
                  {metricsLoading
                    ? "审核中"
                    : metricError
                      ? "未复用固定结果"
                      : isKnowledgeAnswer
                        ? "引用已校验"
                      : agentStatus === "clarification_required"
                        ? "等待回复"
                        : agentStatus === "unsupported"
                          ? "已说明"
                      : evidenceReview?.overall_status === "passed"
                        ? "证据门禁通过"
                        : "需要补证"}
                </strong>
                <ArrowRight size={16} />
                </button>
              )}

              <div className="answer-body">
                <h2 className={agentStatus === "chat" ? "chat-answer-title" : ""}>
                  {metricsLoading
                    ? agentActivity || "正在处理…"
                    : metricError
                      ? "当前问题暂时无法执行。"
                      : agentStatus === "chat"
                        ? typedAgentMessage
                      : isKnowledgeAnswer
                        ? "规则知识已根据版本化来源回答。"
                      : isHybridAnalysis
                        ? "数据与战术知识已完成联合分析。"
                      : agentStatus === "clarification_required"
                        ? "我还需要确认一个分析条件。"
                        : agentStatus === "unsupported"
                          ? "这个问题超出当前已验证能力。"
                      : `${findings.length} 条描述性观察已通过确定性证据门禁。`}
                </h2>
                {agentStatus !== "chat" && (!workspace || isHybridAnalysis) && (
                  <p
                    className={`answer-lead ${
                      isKnowledgeAnswer ? "knowledge-answer" : ""
                    }`}
                  >
                    {metricError
                      ? metricError
                      : isKnowledgeAnswer
                        ? typedAgentMessage
                      : typedAgentMessage}
                  </p>
                )}

                <div className="evidence-points">
                  {findings.map((finding, index) => (
                    <div key={finding.finding_id}>
                      <span className="evidence-number">{index + 1}</span>
                      <p>{finding.statement}</p>
                    </div>
                  ))}
                </div>

                {workspace?.metrics && (
                  <TrendChart
                    metrics={workspace?.metrics ?? null}
                    findingIds={findings.map((finding) => finding.finding_id)}
                    loading={false}
                    error={metricError}
                  />
                )}

                {workspace && (
                  <div className="source-links">
                    <span>数据来源：</span>
                    <button type="button" onClick={onShowEvidence}>
                      [1] StatsBomb Open Data
                    </button>
                    <span>算法：footops-player-role-v1</span>
                    <span>门禁：footops-evidence-gate-v1</span>
                  </div>
                )}

                {isKnowledgeAnswer && citedKnowledge.length > 0 && (
                  <div className="source-links knowledge-sources">
                    <span>规则来源：</span>
                    {citedKnowledge.map((reference) => (
                      <a
                        key={reference.evidence_id}
                        href={reference.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        [{reference.evidence_id.split(":")[1]}] {reference.title}
                        {" · "}
                        {reference.section}
                      </a>
                    ))}
                    <span>{knowledgeEvidence?.corpus_version}</span>
                  </div>
                )}

                <div className="answer-actions">
                  {agentStatus === "chat" || isKnowledgeAnswer ? (
                    <button
                      type="button"
                      onClick={() => inputRef.current?.focus()}
                    >
                      <MessageCircleMore size={16} />
                      继续对话
                    </button>
                  ) : (
                    <>
                  <button
                    type="button"
                    onClick={onShowTactics}
                    disabled={!workspace?.tactics_board}
                  >
                    <Swords size={16} />
                    打开分析战术板
                  </button>
                  <button type="button" disabled>
                    <FileText size={16} />
                    报告尚未生成
                  </button>
                  <button
                    type="button"
                    onClick={() => inputRef.current?.focus()}
                  >
                    <MessageCircleMore size={16} />
                    继续提问
                  </button>
                  <button
                    type="button"
                    onClick={exportAnswer}
                    disabled={!workspace}
                  >
                    <Download size={16} />
                    导出
                  </button>
                    </>
                  )}
                </div>
              </div>
            </article>
          </>
        )}
      </div>

      <form className="chat-composer" onSubmit={submitQuestion}>
        <textarea
          ref={inputRef}
          value={draft}
          rows={2}
          placeholder="例如：分析佩德里在西甲 2020/21 最近五场的角色变化…"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <div className="composer-controls">
          <div>
            <button
              className="icon-button"
              type="button"
              title="添加文件"
              aria-label="添加文件"
            >
              <Paperclip size={18} />
            </button>
            <button
              className={`scope-toggle ${scopeOpen ? "active" : ""}`}
              type="button"
              onClick={() => setScopeOpen((current) => !current)}
              aria-expanded={scopeOpen}
              aria-controls="footops-analysis-scope"
            >
              <SlidersHorizontal size={15} />
              <span>{selectedCompetition ? competitionLabel : "分析范围"}</span>
              <span className="scope-toggle-hint">
                {playerQuery || requestedWindow ? "已设置" : "可选"}
              </span>
            </button>
          </div>
          <button
            className="send-button"
            type="submit"
            title="发送"
            aria-label="发送问题"
            disabled={
              !draft.trim() ||
              isSubmitting ||
              metricsLoading
            }
          >
            <Send size={18} />
          </button>
        </div>
        {scopeOpen && (
          <div className="scope-popover" id="footops-analysis-scope">
            <div className="scope-popover-heading">
              <div>
                <strong>分析范围</strong>
                <span>不填写时由 Agent 根据问题解析</span>
              </div>
              <button
                className="scope-reset"
                type="button"
                onClick={() => {
                  onSelectCompetition("");
                  onPlayerQueryChange("");
                  onRequestedWindowChange(undefined);
                }}
                disabled={!selectedCompetition && !playerQuery && !requestedWindow}
              >
                清除
              </button>
            </div>
            <div className="scope-fields">
              <label>
                <span>赛事</span>
                <select
                  value={
                    selectedCompetition
                      ? `${selectedCompetition.competition_id}:${selectedCompetition.season_id}`
                      : ""
                  }
                  onChange={(event) => onSelectCompetition(event.target.value)}
                  disabled={metricsLoading || competitions.length === 0}
                >
                  <option value="">不限赛事，由 Agent 解析</option>
                  {competitions.map((competition) => (
                    <option
                      key={`${competition.competition_id}:${competition.season_id}`}
                      value={`${competition.competition_id}:${competition.season_id}`}
                    >
                      {competition.competition_name} {competition.season_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>球员</span>
                <input
                  list="footops-player-options"
                  value={playerQuery}
                  placeholder={
                    selectedCompetition
                      ? catalogLoading
                        ? "读取球员…"
                        : "可选球员约束"
                      : "先选赛事"
                  }
                  onChange={(event) => onPlayerQueryChange(event.target.value)}
                  disabled={catalogLoading || !selectedCompetition}
                />
                <datalist id="footops-player-options">
                  {players.map((entry) => (
                    <option
                      key={entry.player.player_id}
                      value={entry.player.player_nickname ?? entry.player.player_name}
                    >
                      {entry.player.player_name} · {entry.appearance_count} 场
                    </option>
                  ))}
                </datalist>
              </label>
              <label>
                <span>比赛窗口</span>
                <select
                  value={requestedWindow ?? ""}
                  onChange={(event) =>
                    onRequestedWindowChange(
                      event.target.value ? Number(event.target.value) : undefined,
                    )
                  }
                  disabled={metricsLoading}
                >
                  <option value="">窗口由 Agent 解析</option>
                  {[2, 3, 5, 8, 10].map((window) => (
                    <option key={window} value={window}>
                      近 {window} 场
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {catalogError && <small className="scope-error">{catalogError}</small>}
          </div>
        )}
        <div className="composer-scope">
          {selectedCompetition
            ? `${resolvedPlayer?.player.player_nickname ?? (playerQuery || "球员由 Agent 解析")} · ${competitionLabel} · ${windowLabel}`
            : `自然语言优先 · ${windowLabel}`}
        </div>
      </form>
    </section>
  );
}
