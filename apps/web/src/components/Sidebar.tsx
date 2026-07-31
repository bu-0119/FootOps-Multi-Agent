import {
  FileText,
  LayoutPanelTop,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  ShieldQuestion,
  Swords,
  UserRoundSearch,
  X,
} from "lucide-react";
import type { ViewKey } from "../types";

interface SidebarProps {
  activeView: ViewKey;
  collapsed: boolean;
  mobileOpen: boolean;
  onSelect: (view: ViewKey) => void;
  onToggle: () => void;
  onCloseMobile: () => void;
  onNewChat: () => void;
  conversationTitle: string | null;
}

const navItems = [
  { id: "chat" as const, label: "足球问答", icon: MessageCircle },
  { id: "matches" as const, label: "比赛研究", icon: Search },
  { id: "players" as const, label: "球员研究", icon: UserRoundSearch },
  { id: "tactics" as const, label: "战术板", icon: Swords },
  { id: "reports" as const, label: "报告", icon: FileText },
];

export function Sidebar({
  activeView,
  collapsed,
  mobileOpen,
  onSelect,
  onToggle,
  onCloseMobile,
  onNewChat,
  conversationTitle,
}: SidebarProps) {
  const selectView = (view: ViewKey) => {
    onSelect(view);
    onCloseMobile();
  };

  return (
    <>
      <button
        className={`sidebar-backdrop ${mobileOpen ? "visible" : ""}`}
        type="button"
        aria-label="关闭侧边栏"
        onClick={onCloseMobile}
      />
      <aside
        className={[
          "sidebar",
          collapsed ? "collapsed" : "",
          mobileOpen ? "mobile-open" : "",
        ].join(" ")}
      >
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </div>
          <div className="brand-copy">
            <strong>FootOps</strong>
            <small>ANALYST</small>
          </div>
          <button
            className="icon-button sidebar-mobile-close"
            type="button"
            title="关闭侧边栏"
            aria-label="关闭侧边栏"
            onClick={onCloseMobile}
          >
            <X size={18} />
          </button>
        </div>

        <button
          className="new-chat-button"
          type="button"
          title={collapsed ? "新建对话" : undefined}
          onClick={onNewChat}
        >
          <Plus size={18} />
          <span>新建对话</span>
        </button>

        <nav className="primary-nav" aria-label="主要功能">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={activeView === item.id ? "active" : ""}
                type="button"
                title={collapsed ? item.label : undefined}
                aria-current={activeView === item.id ? "page" : undefined}
                onClick={() => selectView(item.id)}
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-separator" />

        <section className="history-section" aria-label="对话历史">
          <div className="sidebar-section-title">
            <span>对话历史</span>
            <button
              className="icon-button quiet"
              type="button"
              title="搜索对话"
              aria-label="搜索对话"
            >
              <Search size={15} />
            </button>
          </div>
          <div className="conversation-list">
            {conversationTitle ? (
              <button
                className="active"
                type="button"
                onClick={() => selectView("chat")}
              >
                <MessageCircle size={16} />
                <span>{conversationTitle}</span>
              </button>
            ) : (
              <span className="conversation-empty">暂无分析对话</span>
            )}
          </div>
        </section>

        <div className="sidebar-spacer" />

        <button
          className="sidebar-help"
          type="button"
          title={collapsed ? "数据使用说明" : undefined}
        >
          <ShieldQuestion size={18} />
          <span>数据使用说明</span>
        </button>

        <button
          className="collapse-button"
          type="button"
          onClick={onToggle}
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          <span>{collapsed ? "展开侧边栏" : "收起侧边栏"}</span>
        </button>
      </aside>
    </>
  );
}
