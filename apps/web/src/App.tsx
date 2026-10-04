import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import {
  fetchCompetitionCatalog,
  fetchPlayerCatalog,
  runFootOpsAgent,
  type AgentAnalysisResponse,
  type AgentConversationTurn,
  type AgentRunStreamEvent,
  type CompetitionSeason,
  type PlayerCatalogEntry,
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
  const [rightTab, setRightTab] = useState<RightPanelTab>("evidence");
  const [rightWorkspaceCollapsed, setRightWorkspaceCollapsed] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [workspace, setWorkspace] = useState<AnalysisWorkspace | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [chatKey, setChatKey] = useState(0);
  const [metricError, setMetricError] = useState("");
  const [agentOutcome, setAgentOutcome] = useState<AgentAnalysisResponse | null>(
    null,
  );
  const [agentHistory, setAgentHistory] = useState<AgentConversationTurn[]>([]);
  const [agentActivity, setAgentActivity] = useState("");
  const [agentStreamEvents, setAgentStreamEvents] = useState<AgentRunStreamEvent[]>(
    [],
  );
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [competitions, setCompetitions] = useState<CompetitionSeason[]>([]);
  const [selectedCompetition, setSelectedCompetition] =
    useState<CompetitionSeason | null>(null);
  const [players, setPlayers] = useState<PlayerCatalogEntry[]>([]);
  const [playerQuery, setPlayerQuery] = useState("");
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | undefined>();
  const [requestedWindow, setRequestedWindow] = useState<number | undefined>();
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const analysisController = useRef<AbortController | null>(null);

  useEffect(() => () => analysisController.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    fetchCompetitionCatalog(controller.signal)
      .then((response) => {
        setCompetitions(response.competitions);
        setCatalogError("");
      })
      .catch((error) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setCatalogError(
            error instanceof Error ? error.message : "赛事目录暂时不可用。",
          );
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedCompetition) {
      setPlayers([]);
      setPlayerQuery("");
      setSelectedPlayerId(undefined);
      setCatalogLoading(false);
      return;
    }
    const controller = new AbortController();
    let active = true;
    setCatalogLoading(true);
    setPlayers([]);
    setPlayerQuery("");
    setSelectedPlayerId(undefined);
    fetchPlayerCatalog(
      selectedCompetition.competition_id,
      selectedCompetition.season_id,
      controller.signal,
    )
      .then((response) => {
        if (!active) {
          return;
        }
        setPlayers(response.players);
        setCatalogError("");
      })
      .catch((error) => {
        if (
          active &&
          !(error instanceof DOMException && error.name === "AbortError")
        ) {
          setCatalogError(
            error instanceof Error ? error.message : "球员目录暂时不可用。",
          );
        }
      })
      .finally(() => active && setCatalogLoading(false));
    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedCompetition]);

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
    setRightWorkspaceCollapsed(false);
    document
      .querySelector(".right-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const openEvidence = () => {
    setRightTab("evidence");
    setRightWorkspaceCollapsed(false);
    document
      .querySelector(".right-workspace")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const analyzeQuestion = async (question: string) => {
    analysisController.current?.abort();
    const controller = new AbortController();
    analysisController.current = controller;
    const normalizedQuestion = question.toLocaleLowerCase();
    const isContextualFollowUp = [
      "这名球员",
      "这球员",
      "哪场",
      "哪一场",
      "这几场",
      "其中",
      "射门最多",
      "xg",
      "预期进球",
    ].some((term) => normalizedQuestion.includes(term));
    const previousScope = isContextualFollowUp ? workspace?.request.scope : null;
    const previousCompetition = isContextualFollowUp
      ? workspace?.coverage?.competition
      : null;
    setPendingQuestion(question);
    setWorkspace(null);
    setAgentOutcome(null);
    setAgentActivity("正在处理你的问题");
    setAgentStreamEvents([]);
    setMetricError("");
    setMetricsLoading(true);
    try {
      const response = await runFootOpsAgent(
        question,
        {
          ...(selectedCompetition
            ? {
                competition_id: selectedCompetition.competition_id,
                season_id: selectedCompetition.season_id,
              }
            : previousCompetition
              ? {
                  competition_id: previousCompetition.competition_id,
                  season_id: previousCompetition.season_id,
                }
              : {}),
          ...(playerQuery.trim()
            ? { player: playerQuery.trim() }
            : previousScope
              ? { player: previousScope.player, player_id: previousScope.player_id }
              : {}),
          ...(selectedPlayerId
            ? { player_id: selectedPlayerId }
            : previousScope
              ? { player_id: previousScope.player_id }
              : {}),
          ...(requestedWindow
            ? { requested_window: requestedWindow }
            : previousScope
              ? { requested_window: previousScope.match_ids.length }
              : {}),
        },
        agentHistory,
        controller.signal,
        setAgentActivity,
        (event) => {
          setAgentStreamEvents((current) =>
            [...current.filter((item) => item.sequence !== event.sequence), event]
              .sort((left, right) => left.sequence - right.sequence)
              .slice(-8),
          );
          if (event.response) {
            setAgentOutcome(event.response);
            setWorkspace(event.response.workspace);
          }
        },
      );
      setAgentHistory((current) =>
        [
          ...current,
          { role: "user" as const, content: question },
          { role: "assistant" as const, content: response.message },
        ].slice(-12),
      );
      setAgentOutcome(response);
      setWorkspace(response.workspace);
      setPendingQuestion("");
      setAgentActivity("");
      setToast(
        response.status === "chat"
          ? "已回复"
          : response.knowledge_answer?.status === "answered"
            ? "规则回答已生成"
          : response.status === "completed"
            ? "分析工作区已生成"
            : "Agent 需要补充范围",
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setMetricError(
        error instanceof Error ? error.message : "历史公开比赛数据暂时不可用。",
      );
      setAgentActivity("");
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
    setAgentOutcome(null);
    setAgentHistory([]);
    setAgentActivity("");
    setAgentStreamEvents([]);
    setMetricsLoading(false);
    setChatKey((current) => current + 1);
    openChat();
  };

  const selectCompetition = (value: string) => {
    if (!value) {
      setSelectedCompetition(null);
      return;
    }
    const [competitionId, seasonId] = value.split(":").map(Number);
    const selected = competitions.find(
      (item) =>
        item.competition_id === competitionId && item.season_id === seasonId,
    );
    setSelectedCompetition(selected ?? null);
  };

  const updatePlayerQuery = (value: string) => {
    setPlayerQuery(value);
    const normalized = value.trim().toLocaleLowerCase();
    const selected = players.find((item) => {
      const names = [item.player.player_name, item.player.player_nickname ?? ""];
      return names.some((name) => name.toLocaleLowerCase() === normalized);
    });
    setSelectedPlayerId(selected?.player.player_id);
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
          scopeLabel={
            selectedCompetition
              ? `${selectedCompetition.competition_name} ${selectedCompetition.season_name}`
              : "公开数据目录"
          }
          onToggleSidebar={() =>
            setSidebarCollapsed((current) => !current)
          }
          onOpenMobile={() => setMobileSidebarOpen(true)}
        />

        <main
          className={`workspace ${
            rightWorkspaceCollapsed ? "right-workspace-is-collapsed" : ""
          }`}
        >
          <div className="primary-workspace">
            {activeView === "chat" && (
              <ChatView
                key={chatKey}
                onShowTactics={openBoard}
                onShowEvidence={openEvidence}
                onNotify={setToast}
                onAnalyze={analyzeQuestion}
                workspace={workspace}
                pendingQuestion={pendingQuestion}
                metricsLoading={metricsLoading}
                metricError={metricError}
                agentStatus={agentOutcome?.status ?? null}
                agentMessage={agentOutcome?.message ?? ""}
                isHybridAnalysis={
                  agentOutcome?.execution_plan.intent ===
                  "hybrid_tactical_analysis"
                }
                knowledgeEvidence={agentOutcome?.knowledge_evidence ?? null}
                knowledgeAnswer={agentOutcome?.knowledge_answer ?? null}
                agentActivity={agentActivity}
                competitions={competitions}
                selectedCompetition={selectedCompetition}
                onSelectCompetition={selectCompetition}
                players={players}
                playerQuery={playerQuery}
                onPlayerQueryChange={updatePlayerQuery}
                requestedWindow={requestedWindow}
                onRequestedWindowChange={setRequestedWindow}
                catalogLoading={catalogLoading}
                catalogError={catalogError}
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
            collapsed={rightWorkspaceCollapsed}
            onToggleCollapsed={() =>
              setRightWorkspaceCollapsed((current) => !current)
            }
            onNotify={setToast}
            workspace={workspace}
            metricsLoading={metricsLoading && Boolean(workspace)}
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
