import { useEffect, useMemo, useRef, useState } from "react";
import { toPng } from "html-to-image";
import {
  Download,
  Eraser,
  Eye,
  EyeOff,
  Maximize2,
  MousePointer2,
  MoveUpRight,
  Redo2,
  Save,
  SquareDashed,
  Trash2,
  Undo2,
  UserRoundPlus,
} from "lucide-react";
import type {
  BoardArrow,
  BoardPlayer,
  BoardTool,
  BoardZone,
} from "../types";
import type { TacticsBoardArtifact } from "../api/data";

interface BoardState {
  players: BoardPlayer[];
  arrows: BoardArrow[];
  zones: BoardZone[];
}

interface TacticsBoardProps {
  onNotify: (message: string) => void;
  artifact: TacticsBoardArtifact | null;
}

const originalState: BoardState = {
  players: [],
  arrows: [],
  zones: [],
};

function stateFromArtifact(artifact: TacticsBoardArtifact | null): BoardState {
  if (!artifact) {
    return cloneBoardState(originalState);
  }
  return {
    players: artifact.players.map((player) => ({
      id: player.marker_id,
      number: 0,
      x: player.position.x,
      y: player.position.y,
      role:
        player.role === "focus"
          ? "focus"
          : player.role === "opponent"
            ? "opponent"
            : "home",
      label: player.label,
      displayLabel: player.display_label,
      findingRefs: player.finding_refs,
    })),
    arrows: [...artifact.arrows, ...artifact.passing_lanes].map((arrow) => ({
      id: arrow.arrow_id,
      fromX: arrow.start.x,
      fromY: arrow.start.y,
      toX: arrow.end.x,
      toY: arrow.end.y,
      kind: arrow.kind,
      label: arrow.label,
      findingRefs: arrow.finding_refs,
    })),
    zones: artifact.zones.map((zone) => ({
      id: zone.zone_id,
      x: zone.x,
      y: zone.y,
      width: zone.width,
      height: zone.height,
      label: zone.label,
      findingRefs: zone.finding_refs,
    })),
  };
}

const toolItems = [
  { id: "select" as const, label: "选择与移动", icon: MousePointer2 },
  { id: "arrow" as const, label: "绘制线路", icon: MoveUpRight },
  { id: "zone" as const, label: "标记区域", icon: SquareDashed },
  { id: "player" as const, label: "添加球员", icon: UserRoundPlus },
  { id: "erase" as const, label: "擦除", icon: Eraser },
];

function cloneBoardState(state: BoardState): BoardState {
  return {
    players: state.players.map((player) => ({ ...player })),
    arrows: state.arrows.map((arrow) => ({ ...arrow })),
    zones: state.zones.map((zone) => ({ ...zone })),
  };
}

export function TacticsBoard({ artifact, onNotify }: TacticsBoardProps) {
  const pitchRef = useRef<HTMLDivElement>(null);
  const [board, setBoard] = useState<BoardState>(() =>
    cloneBoardState(originalState),
  );
  const [history, setHistory] = useState<BoardState[]>([
    cloneBoardState(originalState),
  ]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [formation, setFormation] = useState("unassigned");
  const [activeTool, setActiveTool] = useState<BoardTool>("select");
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [arrowStart, setArrowStart] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [layers, setLayers] = useState({
    positions: false,
    heatmap: false,
    routes: false,
  });

  useEffect(() => {
    const next = stateFromArtifact(artifact);
    setBoard(next);
    setHistory([cloneBoardState(next)]);
    setHistoryIndex(0);
    setFormation(artifact?.formation ?? "unassigned");
    setLayers({
      positions: next.players.length > 0,
      heatmap: next.zones.length > 0,
      routes: next.arrows.length > 0,
    });
    setArrowStart(null);
  }, [artifact]);

  const selectedToolLabel = useMemo(
    () => toolItems.find((tool) => tool.id === activeTool)?.label,
    [activeTool],
  );

  const commit = (next: BoardState) => {
    const snapshot = cloneBoardState(next);
    setBoard(snapshot);
    setHistory((current) => [
      ...current.slice(0, historyIndex + 1),
      snapshot,
    ]);
    setHistoryIndex((current) => current + 1);
  };

  const getPoint = (clientX: number, clientY: number) => {
    const rect = pitchRef.current?.getBoundingClientRect();
    if (!rect) {
      return { x: 50, y: 50 };
    }
    return {
      x: Math.max(2, Math.min(98, ((clientX - rect.left) / rect.width) * 100)),
      y: Math.max(2, Math.min(98, ((clientY - rect.top) / rect.height) * 100)),
    };
  };

  const handlePitchClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (draggingId) {
      return;
    }
    const point = getPoint(event.clientX, event.clientY);

    if (activeTool === "arrow") {
      if (!arrowStart) {
        setArrowStart(point);
        onNotify("已选择线路起点");
        return;
      }
      commit({
        ...board,
        arrows: [
          ...board.arrows,
          {
            id: `arrow-${Date.now()}`,
            fromX: arrowStart.x,
            fromY: arrowStart.y,
            toX: point.x,
            toY: point.y,
            kind: "movement",
          },
        ],
      });
      setLayers((current) => ({ ...current, routes: true }));
      setArrowStart(null);
      return;
    }

    if (activeTool === "zone") {
      commit({
        ...board,
        zones: [
          ...board.zones,
          {
            id: `zone-${Date.now()}`,
            x: Math.max(1, point.x - 11),
            y: Math.max(1, point.y - 8),
            width: 22,
            height: 16,
          },
        ],
      });
      setLayers((current) => ({ ...current, heatmap: true }));
      return;
    }

    if (activeTool === "player") {
      const nextNumber =
        Math.max(0, ...board.players.map((player) => player.number)) + 1;
      commit({
        ...board,
        players: [
          ...board.players,
          {
            id: `player-${Date.now()}`,
            number: nextNumber,
            x: point.x,
            y: point.y,
            role: "home",
            label: `球员 ${nextNumber}`,
          },
        ],
      });
      setLayers((current) => ({ ...current, positions: true }));
      return;
    }

    if (activeTool === "erase" && board.zones.length > 0) {
      commit({ ...board, zones: board.zones.slice(0, -1) });
    }
  };

  const startDragging = (
    event: React.PointerEvent<HTMLButtonElement>,
    playerId: string,
  ) => {
    event.stopPropagation();
    if (activeTool === "erase") {
      commit({
        ...board,
        players: board.players.filter((player) => player.id !== playerId),
      });
      return;
    }
    if (activeTool !== "select") {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    setDraggingId(playerId);
  };

  const moveDragging = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingId || activeTool !== "select") {
      return;
    }
    const point = getPoint(event.clientX, event.clientY);
    setBoard((current) => ({
      ...current,
      players: current.players.map((player) =>
        player.id === draggingId ? { ...player, ...point } : player,
      ),
    }));
  };

  const stopDragging = () => {
    if (!draggingId) {
      return;
    }
    const snapshot = cloneBoardState(board);
    setHistory((current) => [
      ...current.slice(0, historyIndex + 1),
      snapshot,
    ]);
    setHistoryIndex((current) => current + 1);
    setDraggingId(null);
  };

  const undo = () => {
    if (historyIndex === 0) {
      return;
    }
    const nextIndex = historyIndex - 1;
    setHistoryIndex(nextIndex);
    setBoard(cloneBoardState(history[nextIndex]));
  };

  const redo = () => {
    if (historyIndex >= history.length - 1) {
      return;
    }
    const nextIndex = historyIndex + 1;
    setHistoryIndex(nextIndex);
    setBoard(cloneBoardState(history[nextIndex]));
  };

  const reset = () => {
    const next = stateFromArtifact(artifact);
    commit(next);
    setArrowStart(null);
    setFormation(artifact?.formation ?? "unassigned");
    setLayers({
      positions: next.players.length > 0,
      heatmap: next.zones.length > 0,
      routes: next.arrows.length > 0,
    });
    onNotify(artifact ? "已恢复审核后的分析图层" : "战术板已清空");
  };

  const updateFormation = (value: string) => {
    setFormation(value);
    const presets: Record<string, Array<[number, number]>> = {
      "4-3-3": [
        [24, 50],
        [49, 54],
        [83, 49],
      ],
      "4-2-3-1": [
        [34, 62],
        [64, 62],
        [49, 42],
      ],
      "3-4-3": [
        [24, 53],
        [43, 57],
        [62, 57],
      ],
    };
    const midfield = presets[value];
    if (!midfield) {
      return;
    }
    const midfieldIds = ["pedri", "dm", "cm"];
    commit({
      ...board,
      players: board.players.map((player) => {
        const index = midfieldIds.indexOf(player.id);
        return index >= 0
          ? { ...player, x: midfield[index][0], y: midfield[index][1] }
          : player;
      }),
    });
  };

  const saveBoard = () => {
    localStorage.setItem(
      "footops:tactics-board",
      JSON.stringify({ formation, ...board }),
    );
    onNotify("战术板已保存到本地");
  };

  const exportBoard = async () => {
    if (!pitchRef.current) {
      return;
    }
    const dataUrl = await toPng(pitchRef.current, {
      pixelRatio: 2,
      backgroundColor: "#ffffff",
      cacheBust: true,
    });
    const link = document.createElement("a");
    link.download = "footops-tactics-board.png";
    link.href = dataUrl;
    link.click();
    onNotify("战术板图片已导出");
  };

  const openFullscreen = async () => {
    await pitchRef.current?.requestFullscreen?.();
  };

  return (
    <div className="tactics-panel-content">
      <div className="board-context-row">
        <label>
          <span className="sr-only">比赛范围</span>
          <select value={artifact ? "artifact" : "manual"} disabled>
            <option value="manual">空白战术板</option>
            <option value="artifact">{artifact?.title ?? "分析战术板"}</option>
          </select>
        </label>
        <label>
          <span className="sr-only">阵型</span>
          <select
            value={formation}
            onChange={(event) => updateFormation(event.target.value)}
          >
            <option value="unassigned">未指定阵型</option>
            <option value="4-3-3">4-3-3</option>
            <option value="4-2-3-1">4-2-3-1</option>
            <option value="3-4-3">3-4-3</option>
          </select>
        </label>
      </div>

      <div className="board-toolbar" aria-label="战术板工具">
        {toolItems.map((tool) => {
          const Icon = tool.icon;
          return (
            <button
              key={tool.id}
              className={activeTool === tool.id ? "active" : ""}
              type="button"
              title={tool.label}
              aria-label={tool.label}
              aria-pressed={activeTool === tool.id}
              onClick={() => {
                setActiveTool(tool.id);
                setArrowStart(null);
              }}
            >
              <Icon size={17} />
            </button>
          );
        })}
        <span className="toolbar-divider" />
        <button
          type="button"
          title="撤销"
          aria-label="撤销"
          disabled={historyIndex === 0}
          onClick={undo}
        >
          <Undo2 size={17} />
        </button>
        <button
          type="button"
          title="重做"
          aria-label="重做"
          disabled={historyIndex >= history.length - 1}
          onClick={redo}
        >
          <Redo2 size={17} />
        </button>
        <button type="button" title="重置" aria-label="重置" onClick={reset}>
          <Trash2 size={17} />
        </button>
        <button
          type="button"
          title="全屏"
          aria-label="全屏"
          onClick={openFullscreen}
        >
          <Maximize2 size={17} />
        </button>
      </div>

      <div className="active-tool-hint">
        {arrowStart ? "请选择线路终点" : selectedToolLabel}
      </div>

      <div
        ref={pitchRef}
        className="tactics-pitch"
        onClick={handlePitchClick}
        onPointerMove={moveDragging}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
        role="application"
        aria-label="可编辑足球战术板"
      >
        <div className="pitch-outline" />
        <div className="pitch-halfway" />
        <div className="center-circle" />
        <div className="center-spot" />
        <div className="penalty-box top" />
        <div className="goal-box top" />
        <div className="goal top" />
        <div className="penalty-spot top" />
        <div className="penalty-box bottom" />
        <div className="goal-box bottom" />
        <div className="goal bottom" />
        <div className="penalty-spot bottom" />

        {board.players.length === 0 &&
          board.arrows.length === 0 &&
          board.zones.length === 0 && (
            <div className="board-empty-state">尚无已审核的战术图层</div>
          )}

        {layers.heatmap &&
          board.zones.map((zone) => (
            <div
              key={zone.id}
              className={`analysis-zone ${zone.id.includes("early") ? "early" : "late"}`}
              title={zone.label}
              style={{
                left: `${zone.x}%`,
                top: `${zone.y}%`,
                width: `${zone.width}%`,
                height: `${zone.height}%`,
              }}
            />
          ))}

        {layers.routes && (
          <svg
            className="pitch-routes"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <defs>
              <marker
                id="arrow-yellow"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="4"
                markerHeight="4"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#f4c430" />
              </marker>
              <marker
                id="arrow-blue"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="4"
                markerHeight="4"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#58a5e8" />
              </marker>
            </defs>
            {board.arrows.map((arrow) => (
              <line
                key={arrow.id}
                x1={arrow.fromX}
                y1={arrow.fromY}
                x2={arrow.toX}
                y2={arrow.toY}
                className={arrow.kind}
                markerEnd={`url(#arrow-${
                  arrow.kind === "movement" ? "yellow" : "blue"
                })`}
              />
            ))}
          </svg>
        )}

        {layers.positions &&
          board.players.map((player) => (
            <button
              key={player.id}
              className={`pitch-player ${player.role}`}
              type="button"
              title={`${player.label} · ${player.displayLabel ?? player.number}`}
              aria-label={`${player.label}，标记 ${player.displayLabel ?? player.number}`}
              style={{
                left: `${player.x}%`,
                top: `${player.y}%`,
              }}
              onPointerDown={(event) => startDragging(event, player.id)}
              onClick={(event) => event.stopPropagation()}
            >
              {player.displayLabel ?? player.number}
            </button>
          ))}

      </div>

      <section className="layer-panel" aria-labelledby="layers-title">
        <div className="layer-panel-title" id="layers-title">
          分析图层
        </div>
        {[
          { key: "positions" as const, label: "样本平均位置", color: "#7c2437" },
          { key: "heatmap" as const, label: "平均触球区域", color: "#89c86f" },
          { key: "routes" as const, label: "样本位置变化", color: "#f4c430" },
        ].map((layer) => (
          <div className="layer-row" key={layer.key}>
            <label>
              <input
                type="checkbox"
                checked={layers[layer.key]}
                onChange={(event) =>
                  setLayers((current) => ({
                    ...current,
                    [layer.key]: event.target.checked,
                  }))
                }
              />
              <span>{layer.label}</span>
            </label>
            <span
              className="layer-color"
              style={{ backgroundColor: layer.color }}
            />
            {layers[layer.key] ? <Eye size={15} /> : <EyeOff size={15} />}
          </div>
        ))}
      </section>

      <div className="board-actions">
        <button type="button" onClick={saveBoard}>
          <Save size={17} />
          保存战术板
        </button>
        <button type="button" onClick={exportBoard}>
          <Download size={17} />
          导出图片
        </button>
      </div>

      <div className="board-source-line">
        {artifact
          ? `${artifact.finding_refs.length} 条已审核 Finding · ${artifact.evidence_refs.length} 个证据引用`
          : "提交分析问题后生成可追溯图层"}
      </div>
    </div>
  );
}
