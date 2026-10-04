import { useEffect, useMemo, useState } from "react";
import type { PlayerRoleMetricArtifact } from "../api/data";

interface TrendChartProps {
  metrics: PlayerRoleMetricArtifact | null;
  findingIds: string[];
  loading: boolean;
  error: string;
}

type ChartMode = "position" | "actions";
type SeriesColor = "green" | "blue" | "gray" | "amber" | "red";

interface ChartSeries {
  findingId: string;
  label: string;
  values: Array<number | null>;
  maximum: number;
  color: SeriesColor;
  format: (value: number | null) => string;
}

function pointsFor(
  values: Array<number | null>,
  maximum: number,
  xPositions: number[],
): string {
  return values
    .map((value, index) => {
      const normalized = value === null ? 0 : Math.min(1, value / maximum);
      return `${xPositions[index]},${165 - normalized * 135}`;
    })
    .join(" ");
}

function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function count(value: number | null): string {
  return value === null ? "—" : `${value}次`;
}

export function TrendChart({ metrics, findingIds, loading, error }: TrendChartProps) {
  const [compact, setCompact] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches,
  );
  const [requestedMode, setRequestedMode] = useState<ChartMode>("position");

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setCompact(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const rows = metrics?.matches ?? [];
  const actionMaximum = useMemo(
    () =>
      Math.max(
        1,
        ...rows.flatMap((row) => [
          row.forward_pass_count,
          row.completed_forward_pass_count,
          row.progressive_carry_count,
          row.key_pass_count,
          row.shot_count,
          row.shot_involvement_count,
        ]),
      ),
    [rows],
  );
  const positionSeries = ([
    {
      findingId: "finding:average_touch_x",
      label: "平均触球纵向位置",
      values: rows.map((row) => row.average_touch_x),
      maximum: 120,
      color: "green",
      format: (value) => (value === null ? "—" : `${value.toFixed(1)}x`),
    },
    {
      findingId: "finding:attacking_third_touch_ratio",
      label: "进攻三区触球占比",
      values: rows.map((row) => row.attacking_third_touch_ratio),
      maximum: 1,
      color: "blue",
      format: percent,
    },
    {
      findingId: "finding:average_receipt_x",
      label: "平均接球纵向位置",
      values: rows.map((row) => row.average_receipt_x),
      maximum: 120,
      color: "gray",
      format: (value) => (value === null ? "—" : `${value.toFixed(1)}x`),
    },
    {
      findingId: "finding:penalty_area_touch_ratio",
      label: "禁区触球占比",
      values: rows.map((row) => row.penalty_area_touch_ratio),
      maximum: 1,
      color: "amber",
      format: percent,
    },
  ] satisfies ChartSeries[]).filter((series) => findingIds.includes(series.findingId));
  const actionSeries = ([
    {
      findingId: "finding:forward_pass_count",
      label: "向前传球",
      values: rows.map((row) => row.forward_pass_count),
      maximum: actionMaximum,
      color: "gray",
      format: count,
    },
    {
      findingId: "finding:completed_forward_pass_count",
      label: "成功向前传球",
      values: rows.map((row) => row.completed_forward_pass_count),
      maximum: actionMaximum,
      color: "green",
      format: count,
    },
    {
      findingId: "finding:progressive_carry_count",
      label: "推进带球",
      values: rows.map((row) => row.progressive_carry_count),
      maximum: actionMaximum,
      color: "blue",
      format: count,
    },
    {
      findingId: "finding:key_pass_count",
      label: "关键传球",
      values: rows.map((row) => row.key_pass_count),
      maximum: actionMaximum,
      color: "amber",
      format: count,
    },
    {
      findingId: "finding:shot_count",
      label: "射门",
      values: rows.map((row) => row.shot_count),
      maximum: actionMaximum,
      color: "gray",
      format: count,
    },
    {
      findingId: "finding:expected_goals",
      label: "预期进球 xG",
      values: rows.map((row) => row.expected_goals),
      maximum: Math.max(0.1, ...rows.map((row) => row.expected_goals ?? 0)),
      color: "red",
      format: (value) => (value === null ? "—" : `${value.toFixed(2)} xG`),
    },
    {
      findingId: "finding:shot_involvement_count",
      label: "射门参与",
      values: rows.map((row) => row.shot_involvement_count),
      maximum: actionMaximum,
      color: "amber",
      format: count,
    },
  ] satisfies ChartSeries[]).filter((series) => findingIds.includes(series.findingId));
  const xgSeries = actionSeries.find(
    (series) => series.findingId === "finding:expected_goals",
  );
  const displayedActionSeries = xgSeries ? [xgSeries] : actionSeries;
  const mode =
    requestedMode === "position" && positionSeries.length === 0
      ? "actions"
      : requestedMode === "actions" && displayedActionSeries.length === 0
        ? "position"
        : requestedMode;
  const series = mode === "position" ? positionSeries : displayedActionSeries;
  const chartWidth = compact ? 360 : 620;
  const gridRight = compact ? 320 : 582;
  const valueX = compact ? 284 : 548;
  const plotStart = compact ? 52 : 60;
  const plotEnd = compact ? 274 : 526;
  const xPositions = rows.map((_, index) =>
    rows.length === 1
      ? (plotStart + plotEnd) / 2
      : plotStart + (index * (plotEnd - plotStart)) / (rows.length - 1),
  );
  const lastX = xPositions.at(-1) ?? plotEnd;
  const playerLabel =
    metrics?.player.player_nickname ?? metrics?.player.player_name ?? "所选球员";
  const xgMaximum = xgSeries?.maximum ?? 0;
  const axisLabels =
    mode === "position"
      ? ["100%", "67%", "33%", "0"]
      : xgSeries
        ? [xgMaximum.toFixed(2), (xgMaximum * 2 / 3).toFixed(2), (xgMaximum / 3).toFixed(2), "0 xG"]
        : [
          String(actionMaximum),
          String(Math.round((actionMaximum * 2) / 3)),
          String(Math.round(actionMaximum / 3)),
          "0",
        ];

  return (
    <figure className="trend-chart" aria-labelledby="trend-chart-title">
      <figcaption id="trend-chart-title">
        <div>
          <strong>{rows.length || "多"}场指标趋势</strong>
          <span>{playerLabel} · 历史公开比赛数据</span>
        </div>
        {positionSeries.length > 0 && actionSeries.length > 0 && (
          <div className="chart-mode-switch" aria-label="指标类型">
            <button
              type="button"
              className={mode === "position" ? "active" : ""}
              aria-pressed={mode === "position"}
              onClick={() => setRequestedMode("position")}
            >
              位置
            </button>
            <button
              type="button"
              className={mode === "actions" ? "active" : ""}
              aria-pressed={mode === "actions"}
              onClick={() => setRequestedMode("actions")}
            >
              推进进攻
            </button>
          </div>
        )}
      </figcaption>
      {loading && <div className="chart-state">正在读取真实比赛事件…</div>}
      {!loading && error && <div className="chart-state error">{error}</div>}
      {!loading && !error && rows.length > 0 && series.length > 0 && (
        <>
          <div className="chart-legend" aria-hidden="true">
            {series.map((item) => (
              <span key={item.findingId} className={item.color}>
                {item.label}
              </span>
            ))}
          </div>
          <svg
            viewBox={`0 0 ${chartWidth} 190`}
            role="img"
            aria-label={`${playerLabel}连续${rows.length}场${mode === "position" ? "位置" : "推进进攻"}指标`}
          >
            <g className="chart-grid">
              <line x1="42" y1="30" x2={gridRight} y2="30" />
              <line x1="42" y1="75" x2={gridRight} y2="75" />
              <line x1="42" y1="120" x2={gridRight} y2="120" />
              <line x1="42" y1="165" x2={gridRight} y2="165" />
            </g>
            <g className="chart-axis">
              {axisLabels.map((label, index) => (
                <text key={label + index} x="14" y={34 + index * 45}>
                  {label}
                </text>
              ))}
              {rows.map((row, index) => (
                <text key={row.match_id} x={xPositions[index] - 11} y="184">
                  {row.match_date.slice(5)}
                </text>
              ))}
            </g>
            {series.map((item, index) => {
              const lastValue = item.values.at(-1) ?? null;
              const normalized = lastValue === null ? 0 : lastValue / item.maximum;
              return (
                <g key={item.findingId}>
                  <polyline
                    className={`series ${item.color}`}
                    points={pointsFor(item.values, item.maximum, xPositions)}
                  />
                  <circle
                    className={`point ${item.color}`}
                    cx={lastX}
                    cy={165 - Math.min(1, normalized) * 135}
                    r="5"
                  />
                  <text
                    className={`chart-value ${item.color}`}
                    x={valueX}
                    y={42 + index * 15}
                  >
                    {item.format(lastValue)}
                  </text>
                </g>
              );
            })}
          </svg>
        </>
      )}
      {!loading && !error && rows.length > 0 && series.length === 0 && (
        <div className="chart-state">当前问题没有可绘制的趋势指标。</div>
      )}
    </figure>
  );
}
