import { useState } from "react";
import { type ChartPoint, type Severity } from "../data/dashboardData";

const severityDot: Record<Severity, string> = {
  Critical: "#f97316",
  Elevated: "#f59e0b",
  Watching: "#14b8a6",
};

const severityText: Record<Severity, string> = {
  Critical: "text-ember",
  Elevated: "text-signal",
  Watching: "text-surge",
};

const width = 920;
const height = 360;
const padding = { top: 24, right: 26, bottom: 38, left: 58 };

function formatTimestampLabel(timestamp: string) {
  return `${timestamp} local`;
}

function getDeviation(actual: number, expectedMin: number, expectedMax: number) {
  const midpoint = (expectedMin + expectedMax) / 2;
  return ((actual - midpoint) / midpoint) * 100;
}

export function AnomalyOverviewChart({ points }: { points: ChartPoint[] }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(points.length - 1);

  const values = points.flatMap((point) => [point.actual, point.expectedMin, point.expectedMax]);
  const minValue = Math.min(...values) - 1;
  const maxValue = Math.max(...values) + 1;
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const xStep = innerWidth / Math.max(points.length - 1, 1);

  const xForIndex = (index: number) => padding.left + index * xStep;
  const yForValue = (value: number) =>
    padding.top + ((maxValue - value) / (maxValue - minValue || 1)) * innerHeight;

  const expectedUpperPath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xForIndex(index)} ${yForValue(point.expectedMax)}`)
    .join(" ");
  const expectedLowerPath = points
    .map((_, index) => `L ${xForIndex(points.length - 1 - index)} ${yForValue(points[points.length - 1 - index].expectedMin)}`)
    .join(" ");
  const expectedBandPath = `${expectedUpperPath} ${expectedLowerPath} Z`;

  const actualLinePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xForIndex(index)} ${yForValue(point.actual)}`)
    .join(" ");

  const centerLinePath = points
    .map((point, index) => {
      const midpoint = (point.expectedMin + point.expectedMax) / 2;
      return `${index === 0 ? "M" : "L"} ${xForIndex(index)} ${yForValue(midpoint)}`;
    })
    .join(" ");

  const anomalyWindows: Array<{ start: number; end: number; severity: Severity }> = [];
  let activeWindow: { start: number; end: number; severity: Severity } | null = null;

  points.forEach((point, index) => {
    const isOutOfBand = point.actual > point.expectedMax || point.actual < point.expectedMin;
    if (!isOutOfBand) {
      if (activeWindow) {
        anomalyWindows.push(activeWindow);
        activeWindow = null;
      }
      return;
    }

    if (!activeWindow) {
      activeWindow = { start: index, end: index, severity: point.severity };
      return;
    }

    activeWindow.end = index;
    if (point.severity === "Critical" || activeWindow.severity === "Watching") {
      activeWindow.severity = point.severity;
    }
  });

  if (activeWindow) {
    anomalyWindows.push(activeWindow);
  }

  const hoveredPoint = hoveredIndex !== null ? points[hoveredIndex] : null;
  const hoveredX = hoveredIndex !== null ? xForIndex(hoveredIndex) : null;
  const hoveredY = hoveredPoint ? yForValue(hoveredPoint.actual) : null;

  return (
    <div className="relative">
      <div className="rounded-[24px] border border-[rgba(120,160,255,0.1)] bg-[rgba(11,18,32,0.96)] p-3 sm:p-4">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-[324px] w-full sm:h-[336px]"
          role="img"
          aria-label="Excursion trace showing vibration against operating tolerance"
          onMouseLeave={() => setHoveredIndex(points.length - 1)}
        >
          {[0, 1, 2, 3].map((tick) => {
            const value = minValue + ((maxValue - minValue) / 3) * tick;
            const y = yForValue(value);

            return (
              <g key={tick}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke="rgba(148,163,184,0.12)" strokeDasharray="5 8" />
                <text x={16} y={y + 4} fill="rgba(148,163,184,0.74)" fontSize="12" fontFamily="var(--font-mono)">
                  {value.toFixed(0)} mm/s
                </text>
              </g>
            );
          })}

          {points.map((point, index) => (
            <g key={point.timestamp}>
              <line
                x1={xForIndex(index)}
                x2={xForIndex(index)}
                y1={padding.top}
                y2={height - padding.bottom}
                stroke="rgba(148,163,184,0.07)"
              />
              {index < points.length - 1 ? null : (
                <text
                  x={xForIndex(index)}
                  y={height - 12}
                  textAnchor="middle"
                  fill="rgba(148,163,184,0.72)"
                  fontSize="12"
                  fontFamily="var(--font-mono)"
                >
                  {point.timestamp}
                </text>
              )}
              {index % 3 === 0 && index < points.length - 1 ? (
                <text
                  x={xForIndex(index)}
                  y={height - 12}
                  textAnchor="middle"
                  fill="rgba(148,163,184,0.72)"
                  fontSize="12"
                  fontFamily="var(--font-mono)"
                >
                  {point.timestamp}
                </text>
              ) : null}
            </g>
          ))}

          {anomalyWindows.map((window, index) => {
            const startX = xForIndex(window.start) - xStep / 2;
            const endX = xForIndex(window.end) + xStep / 2;
            const tone = window.severity === "Critical" ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.075)";

            return (
              <rect
                key={`${window.start}-${window.end}-${index}`}
                x={Math.max(padding.left, startX)}
                y={padding.top}
                width={Math.min(width - padding.right, endX) - Math.max(padding.left, startX)}
                height={innerHeight}
                fill={tone}
              />
            );
          })}

          <path d={expectedBandPath} fill="rgba(59,130,246,0.12)" stroke="rgba(59,130,246,0.1)" strokeWidth="1" />
          <path d={centerLinePath} fill="none" stroke="rgba(148,163,184,0.28)" strokeDasharray="6 7" strokeWidth="1" />
          <path d={actualLinePath} fill="none" stroke="#f3f7fa" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />

          {points.map((point, index) => {
            const isAnomaly = point.actual > point.expectedMax || point.actual < point.expectedMin;
            return (
              <g
                key={`${point.timestamp}-marker`}
                onMouseEnter={() => setHoveredIndex(index)}
                className="cursor-pointer"
              >
                <circle
                  cx={xForIndex(index)}
                  cy={yForValue(point.actual)}
                  r={hoveredIndex === index ? 6 : 3.8}
                  fill={isAnomaly ? severityDot[point.severity] : "#f3f7fa"}
                  stroke={isAnomaly ? "rgba(255,255,255,0.28)" : "rgba(11,18,32,0.9)"}
                  strokeWidth={hoveredIndex === index ? 2 : 1.5}
                />
              </g>
            );
          })}

          {hoveredPoint && hoveredX !== null && hoveredY !== null ? (
            <g>
              <line
                x1={hoveredX}
                x2={hoveredX}
                y1={padding.top}
                y2={height - padding.bottom}
                stroke="rgba(148,163,184,0.34)"
                strokeDasharray="4 6"
              />
              <circle cx={hoveredX} cy={hoveredY} r={8} fill="transparent" stroke="rgba(59,130,246,0.3)" strokeWidth="1.5" />
            </g>
          ) : null}
        </svg>
      </div>

      {hoveredPoint && hoveredX !== null && hoveredY !== null ? (
        <div
          className="pointer-events-none absolute z-10 w-[94px] rounded-[7px] border border-[rgba(120,160,255,0.01)] bg-[rgba(11,18,32,0.62)] p-[1.5px] shadow-[0_1px_2px_rgba(0,0,0,0.05)]"
          style={{
            left: `clamp(12px, calc(${((hoveredX / width) * 100).toFixed(2)}% - 47px), calc(100% - 106px))`,
            top: hoveredY < 110 ? hoveredY + 2 : hoveredY - 31,
          }}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="dashboard-meta text-mist/44">Time</p>
              <p className="mt-0.5 text-[8.5px] font-medium text-white">{formatTimestampLabel(hoveredPoint.timestamp)}</p>
            </div>
            <span className={`dashboard-meta ${severityText[hoveredPoint.severity]}`}>{hoveredPoint.severity}</span>
          </div>

          <div className="mt-0.5 space-y-px text-[8px]">
            <div className="flex items-center justify-between gap-2">
              <span className="dashboard-meta text-mist/52">Actual</span>
              <span className="font-mono font-semibold text-white">{hoveredPoint.actual.toFixed(1)} mm/s</span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="dashboard-meta text-mist/52">Tolerance</span>
              <span className="font-mono font-semibold text-white">
                {hoveredPoint.expectedMin.toFixed(1)}-{hoveredPoint.expectedMax.toFixed(1)} mm/s
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="dashboard-meta text-mist/52">Deviation</span>
              <span className="font-mono font-semibold text-ember">{getDeviation(hoveredPoint.actual, hoveredPoint.expectedMin, hoveredPoint.expectedMax).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
