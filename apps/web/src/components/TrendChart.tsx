import { useEffect, useState } from "react";
import type { PlayerRoleMetricArtifact } from "../api/data";

interface TrendChartProps {
  metrics: PlayerRoleMetricArtifact | null;
  findingIds: string[];
  loading: boolean;
  error: string;
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

export function TrendChart({ metrics, findingIds, loading, error }: TrendChartProps) {
  const [compact, setCompact] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches,
  );

  useEffect(() => {
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setCompact(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const rows = metrics?.matches ?? [];
  const averageTouchX = rows.map((row) => row.average_touch_x);
  const attackingThird = rows.map((row) => row.attacking_third_touch_ratio);
  const averageReceiptX = rows.map((row) => row.average_receipt_x);
  const showTouch = findingIds.includes("finding:average_touch_x");
  const showAttackingThird = findingIds.includes(
    "finding:attacking_third_touch_ratio",
  );
  const showReceipt = findingIds.includes("finding:average_receipt_x");
  const last = rows.at(-1);
  const chartWidth = compact ? 360 : 620;
  const xPositions = compact
    ? [52, 116, 180, 244, 304]
    : [60, 184, 308, 432, 556];
  const gridRight = compact ? 320 : 582;
  const valueX = compact ? 314 : 568;

  return (
    <figure className="trend-chart" aria-labelledby="trend-chart-title">
      <figcaption id="trend-chart-title">
        <strong>五场持球区域指标</strong>
        <span>西甲 2020/21 历史公开样例</span>
      </figcaption>
      {loading && <div className="chart-state">正在读取真实比赛事件…</div>}
      {!loading && error && <div className="chart-state error">{error}</div>}
      {!loading && !error && rows.length > 0 && (
        <>
          <div className="chart-legend" aria-hidden="true">
            {showTouch && <span className="green">平均触球纵向坐标</span>}
            {showAttackingThird && (
              <span className="blue">进攻三区触球占比</span>
            )}
            {showReceipt && <span className="gray">平均接球纵向坐标</span>}
          </div>
          <svg
            viewBox={`0 0 ${chartWidth} 190`}
            role="img"
            aria-label="佩德里西甲 2020/21 连续五场真实持球区域指标"
          >
        <g className="chart-grid">
          <line x1="42" y1="30" x2={gridRight} y2="30" />
          <line x1="42" y1="75" x2={gridRight} y2="75" />
          <line x1="42" y1="120" x2={gridRight} y2="120" />
          <line x1="42" y1="165" x2={gridRight} y2="165" />
        </g>
        <g className="chart-axis">
          <text x="12" y="34">100%</text>
          <text x="17" y="79">67%</text>
          <text x="17" y="124">33%</text>
          <text x="20" y="169">0</text>
          {rows.map((row, index) => (
            <text key={row.match_id} x={xPositions[index] - 11} y="184">
              {row.match_date.slice(5)}
            </text>
          ))}
        </g>
        {showTouch && (
          <>
            <polyline className="series green" points={pointsFor(averageTouchX, 120, xPositions)} />
            <circle className="point green" cx={xPositions[4]} cy={165 - ((last?.average_touch_x ?? 0) / 120) * 135} r="5" />
            <text className="chart-value green" x={valueX} y="48">{last?.average_touch_x?.toFixed(1) ?? "—"}x</text>
          </>
        )}
        {showAttackingThird && (
          <>
            <polyline className="series blue" points={pointsFor(attackingThird, 1, xPositions)} />
            <circle className="point blue" cx={xPositions[4]} cy={165 - (last?.attacking_third_touch_ratio ?? 0) * 135} r="5" />
            <text className="chart-value blue" x={valueX} y="62">{percent(last?.attacking_third_touch_ratio ?? null)}</text>
          </>
        )}
        {showReceipt && (
          <>
            <polyline className="series gray" points={pointsFor(averageReceiptX, 120, xPositions)} />
            <circle className="point gray" cx={xPositions[4]} cy={165 - ((last?.average_receipt_x ?? 0) / 120) * 135} r="5" />
            <text className="chart-value gray" x={valueX} y="76">{last?.average_receipt_x?.toFixed(1) ?? "—"}x</text>
          </>
        )}
          </svg>
        </>
      )}
    </figure>
  );
}
