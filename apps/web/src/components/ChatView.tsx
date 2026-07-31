import { FormEvent, useRef, useState } from "react";
import {
  ArrowRight,
  Download,
  FileText,
  Link2,
  MessageCircleMore,
  Paperclip,
  ScanSearch,
  Send,
  Swords,
} from "lucide-react";
import { type AnalysisWorkspace } from "../api/data";
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
}: ChatViewProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedQuestion, setSubmittedQuestion] = useState("");
  const metricRows = workspace?.metrics?.matches ?? [];
  const findings = workspace?.findings ?? [];
  const evidenceReview = workspace?.evidence_review;
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
    activeQuestion || workspace || metricsLoading || metricError,
  );

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
      "FootOps 历史公开样例指标",
      "",
      "球员：Pedro González López（Pedri）",
      "赛事：西甲 2020/2021",
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
            <p>当前数据范围：Pedri · 西甲 2020/21 · 连续五场公开事件数据</p>
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

              <button
                className="verification-status"
                type="button"
                onClick={onShowEvidence}
              >
                <span>
                  <Link2 size={16} />
                  {metricsLoading
                    ? "正在读取历史公开比赛数据"
                    : metricError
                      ? "真实数据暂时不可用"
                      : `已审核 ${findings.length} 条描述性观察`}
                </span>
                <strong>
                  {metricsLoading
                    ? "审核中"
                    : metricError
                      ? "未使用演示值替代"
                      : evidenceReview?.overall_status === "passed"
                        ? "证据门禁通过"
                        : "需要补证"}
                </strong>
                <ArrowRight size={16} />
              </button>

              <div className="answer-body">
                <h2>
                  {metricsLoading
                    ? "正在建立可复算的描述性观察。"
                    : metricError
                      ? "描述性观察暂时不可用。"
                      : `${findings.length} 条描述性观察已通过确定性证据门禁。`}
                </h2>
                <p className="answer-lead">
                  当前样例来自西甲 2020/21 历史公开数据。下面只展示可复算的样本内
                  比较，不把数值变化提前解释为战术角色变化。
                </p>

                <div className="evidence-points">
                  {findings.map((finding, index) => (
                    <div key={finding.finding_id}>
                      <span className="evidence-number">{index + 1}</span>
                      <p>{finding.statement}</p>
                    </div>
                  ))}
                </div>

                <TrendChart
                  metrics={workspace?.metrics ?? null}
                  loading={metricsLoading}
                  error={metricError}
                />

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

                <div className="answer-actions">
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
          placeholder="询问 Pedri 最近五场的位置或持球变化…"
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
            <label>
              <span className="sr-only">赛事范围</span>
              <select defaultValue="laliga">
                <option value="laliga">西甲 20/21</option>
              </select>
            </label>
            <label>
              <span className="sr-only">分析模式</span>
              <select defaultValue="tactical">
                <option value="tactical">战术分析</option>
              </select>
            </label>
          </div>
          <button
            className="send-button"
            type="submit"
            title="发送"
            aria-label="发送问题"
            disabled={!draft.trim() || isSubmitting || metricsLoading}
          >
            <Send size={18} />
          </button>
        </div>
        <div className="composer-scope">
          当前范围：西甲 2020/21 · 5 场历史样例 · 1 个公开数据源
        </div>
      </form>
    </section>
  );
}
