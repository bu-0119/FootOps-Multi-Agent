import type { RightPanelTab } from "../types";
import type { AnalysisWorkspace } from "../api/data";
import { EvidencePanel } from "./EvidencePanel";
import { TacticsBoard } from "./TacticsBoard";

interface RightWorkspaceProps {
  activeTab: RightPanelTab;
  onChangeTab: (tab: RightPanelTab) => void;
  onNotify: (message: string) => void;
  workspace: AnalysisWorkspace | null;
  metricsLoading: boolean;
  metricError: string;
}

export function RightWorkspace({
  activeTab,
  onChangeTab,
  onNotify,
  workspace,
  metricsLoading,
  metricError,
}: RightWorkspaceProps) {
  return (
    <aside className="right-workspace">
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
    </aside>
  );
}
