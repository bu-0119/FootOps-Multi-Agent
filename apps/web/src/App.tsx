import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import {
  createPlayerRoleWorkspace,
  type AnalysisWorkspace,
} from "./api/data";
import { ChatView } from "./components/ChatView";
import {
  MatchesView,
  PlayersView,
  ReportsView,
  TacticsLibraryView,
} from "./components/ResearchViews";
import { RightWorkspace } from "./components/RightWorkspace";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import type { RightPanelTab, ViewKey } from "./types";

const titles: Record<ViewKey, string> = {
  chat: "足球问答",
  matches: "比赛研究",
  players: "球员研究",
  tactics: "战术板",
  reports: "报告",
};

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("chat");
  const [rightTab, setRightTab] = useState<RightPanelTab>("tactics");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [workspace, setWorkspace] = useState<AnalysisWorkspace | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [chatKey, setChatKey] = useState(0);
  const [metricError, setMetricError] = useState("");
  const [metricsLoading, setMetricsLoading] = useState(false);
  const analysisController = useRef<AbortController | null>(null);

  useEffect(() => () => analysisController.current?.abort(), []);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = window.setTimeout(() => setToast(""), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const openChat = () => {
    setActiveView("chat");
    setMobileSidebarOpen(false);
  };

  const openBoard = () => {
    setRightTab("tactics");
    document
      .querySelector(".right-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const analyzeQuestion = async (question: string) => {
    analysisController.current?.abort();
    const controller = new AbortController();
    analysisController.current = controller;
    setPendingQuestion(question);
    setWorkspace(null);
    setMetricError("");
    setMetricsLoading(true);
    try {
      const response = await createPlayerRoleWorkspace(
        question,
        controller.signal,
        setToast,
      );
      setWorkspace(response.workspace);
      setPendingQuestion("");
      setToast("分析工作区已生成");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setMetricError(
        error instanceof Error ? error.message : "历史公开比赛数据暂时不可用。",
      );
    } finally {
      if (analysisController.current === controller) {
        setMetricsLoading(false);
      }
    }
  };

  const startNewChat = () => {
    analysisController.current?.abort();
    setWorkspace(null);
    setPendingQuestion("");
    setMetricError("");
    setMetricsLoading(false);
    setChatKey((current) => current + 1);
    openChat();
  };

  const viewActions = {
    onOpenChat: openChat,
    onOpenBoard: openBoard,
    onNotify: setToast,
    workspace,
    metricsLoading,
    metricError,
  };

  return (
    <div
      className={`app-shell ${
        sidebarCollapsed ? "sidebar-is-collapsed" : ""
      }`}
    >
      <Sidebar
        activeView={activeView}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileSidebarOpen}
        onSelect={setActiveView}
        onToggle={() => setSidebarCollapsed((current) => !current)}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        conversationTitle={workspace?.request.question ?? null}
        onNewChat={startNewChat}
      />

      <div className="app-frame">
        <Topbar
          collapsed={sidebarCollapsed}
          title={titles[activeView]}
          dataRetrievedAt={workspace?.metrics?.generated_at ?? null}
          onToggleSidebar={() =>
            setSidebarCollapsed((current) => !current)
          }
          onOpenMobile={() => setMobileSidebarOpen(true)}
        />

        <main className="workspace">
          <div className="primary-workspace">
            {activeView === "chat" && (
              <ChatView
                key={chatKey}
                onShowTactics={openBoard}
                onShowEvidence={() => setRightTab("evidence")}
                onNotify={setToast}
                onAnalyze={analyzeQuestion}
                workspace={workspace}
                pendingQuestion={pendingQuestion}
                metricsLoading={metricsLoading}
                metricError={metricError}
              />
            )}
            {activeView === "matches" && <MatchesView {...viewActions} />}
            {activeView === "players" && <PlayersView {...viewActions} />}
            {activeView === "tactics" && (
              <TacticsLibraryView
                workspace={workspace}
                onOpenBoard={openBoard}
              />
            )}
            {activeView === "reports" && <ReportsView />}
          </div>

          <RightWorkspace
            activeTab={rightTab}
            onChangeTab={setRightTab}
            onNotify={setToast}
            workspace={workspace}
            metricsLoading={metricsLoading}
            metricError={metricError}
          />
        </main>
      </div>

      <div className={`toast ${toast ? "visible" : ""}`} role="status">
        <CheckCircle2 size={17} />
        <span>{toast}</span>
      </div>
    </div>
  );
}
