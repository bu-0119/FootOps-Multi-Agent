import type { RightPanelTab } from "../types";
import type { AnalysisWorkspace } from "../api/data";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { EvidencePanel } from "./EvidencePanel";
import { TacticsBoard } from "./TacticsBoard";

interface RightWorkspaceProps {
  activeTab: RightPanelTab;
  onChangeTab: (tab: RightPanelTab) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onNotify: (message: string) => void;
  workspace: AnalysisWorkspace | null;
  metricsLoading: boolean;
  metricError: string;
}

export function RightWorkspace({
  activeTab,
  onChangeTab,
  collapsed,
  onToggleCollapsed,
  onNotify,
  workspace,
  metricsLoading,
  metricError,
}: RightWorkspaceProps) {
  return (
    <aside className={`right-workspace ${collapsed ? "collapsed" : ""}`}>
      {collapsed ? (
        <button
          className="right-workspace-expand"
          type="button"
          title="展开分析面板"
          aria-label="展开分析面板"
          onClick={onToggleCollapsed}
        >
          <PanelRightOpen size={18} />
        </button>
      ) : (
        <>
      <div className="right-tabs" role="tablist" aria-label="分析辅助面板">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "tactics"}
          className={activeTab === "tactics" ? "active" : ""}
          onClick={() => onChangeTab("tactics")}
        >
          战术板
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "evidence"}
          className={activeTab === "evidence" ? "active" : ""}
          onClick={() => onChangeTab("evidence")}
        >
          证据
        </button>
      </div>
      <div className="right-panel-body">
        {activeTab === "tactics" ? (
          <TacticsBoard
            artifact={workspace?.tactics_board ?? null}
            onNotify={onNotify}
          />
        ) : (
          <EvidencePanel
            workspace={workspace}
            loading={metricsLoading}
            error={metricError}
          />
        )}
      </div>
      <button
        className="right-workspace-collapse"
        type="button"
        title="收起分析面板"
        aria-label="收起分析面板"
        onClick={onToggleCollapsed}
      >
        <PanelRightClose size={16} />
        <span>收起面板</span>
      </button>
        </>
      )}
    </aside>
  );
}
