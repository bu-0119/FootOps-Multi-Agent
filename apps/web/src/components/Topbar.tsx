import {
  Bell,
  CircleHelp,
  Clock3,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

interface TopbarProps {
  collapsed: boolean;
  title: string;
  dataRetrievedAt: string | null;
  scopeLabel: string;
  onToggleSidebar: () => void;
  onOpenMobile: () => void;
}

export function Topbar({
  collapsed,
  title,
  dataRetrievedAt,
  scopeLabel,
  onToggleSidebar,
  onOpenMobile,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar-leading">
        <button
          className="icon-button mobile-menu-button"
          type="button"
          title="打开侧边栏"
          aria-label="打开侧边栏"
          onClick={onOpenMobile}
        >
          <Menu size={20} />
        </button>
        <button
          className="icon-button desktop-sidebar-toggle"
          type="button"
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
          onClick={onToggleSidebar}
        >
          {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
        </button>
        <h1>{title}</h1>
        <span className="competition-scope-label">{scopeLabel}</span>
      </div>

      <div className="topbar-actions">
        <div className="freshness">
          <span aria-hidden="true" />
          <span>
            {dataRetrievedAt
              ? `数据载入：${new Date(dataRetrievedAt).toLocaleDateString("zh-CN")}`
              : "等待分析"}
          </span>
        </div>
        <button
          className="icon-button"
          type="button"
          title="最近活动"
          aria-label="最近活动"
        >
          <Clock3 size={19} />
        </button>
        <button
          className="icon-button notification-button"
          type="button"
          title="通知"
          aria-label="通知"
        >
          <Bell size={19} />
        </button>
        <button
          className="icon-button"
          type="button"
          title="帮助"
          aria-label="帮助"
        >
          <CircleHelp size={19} />
        </button>
        <button className="avatar-button" type="button" title="账户">
          DA
        </button>
      </div>
    </header>
  );
}
