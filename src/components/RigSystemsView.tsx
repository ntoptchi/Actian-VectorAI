import { useMemo, useState } from "react";
import type { AssetNode, AssetStatus, RigTopologyConfig, Zone } from "../data/dashboardData";

const statusStyles: Record<
  AssetStatus,
  {
    dot: string;
    badge: string;
    ring: string;
  }
> = {
  normal: {
    dot: "#14b8a6",
    badge: "border-surge/28 bg-surge/10 text-surge",
    ring: "rgba(20,184,166,0.24)",
  },
  watch: {
    dot: "#22d3ee",
    badge: "border-cyan/28 bg-cyan/10 text-cyan",
    ring: "rgba(34,211,238,0.24)",
  },
  warning: {
    dot: "#f59e0b",
    badge: "border-warning/30 bg-warning/10 text-warning",
    ring: "rgba(245,158,11,0.28)",
  },
  critical: {
    dot: "#f97316",
    badge: "border-danger/32 bg-danger/10 text-ember",
    ring: "rgba(249,115,22,0.24)",
  },
  offline: {
    dot: "#64748b",
    badge: "border-white/12 bg-white/5 text-mist/56",
    ring: "rgba(100,116,139,0.26)",
  },
};

function formatStatus(status: AssetStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function topologyStats(config: RigTopologyConfig) {
  const active = config.assets.filter((asset) => asset.status !== "normal" && asset.status !== "offline").length;
  const critical = config.assets.filter((asset) => asset.status === "critical").length;
  return {
    total: config.assets.length,
    active,
    critical,
  };
}

const NODE_RADIUS = 1.8;
const SELECTED_NODE_RADIUS = 2.4;
const NODE_MIN_Y_OFFSET = 14.9;
const NODE_BOTTOM_INSET = 3.4;
const NODE_LABEL_OFFSET = 5.4;
const NODE_LABEL_BOTTOM_INSET = 1.4;
const TOPOLOGY_SCALE = 1.15;
const TOPOLOGY_TRANSLATE_X = (100 * (1 - TOPOLOGY_SCALE)) / 2;
const TOPOLOGY_TRANSLATE_Y = (86 * (1 - TOPOLOGY_SCALE)) / 2;

function truncateZoneTitle(label: string, maxChars: number) {
  const budget = Math.max(6, maxChars);
  if (label.length <= budget) {
    return label;
  }
  return `${label.slice(0, Math.max(0, budget - 1)).trimEnd()}…`;
}

function trimLineWithEllipsis(line: string, maxChars: number) {
  const budget = Math.max(6, maxChars);
  if (line.length <= budget) {
    return line;
  }
  return `${line.slice(0, Math.max(0, budget - 1)).trimEnd()}…`;
}

function wrapZoneDescription(description: string, maxCharsPerLine: number, maxLines = 2) {
  const words = description.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxCharsPerLine) {
      current = candidate;
      continue;
    }

    if (current) {
      lines.push(current);
      current = word;
    } else {
      lines.push(trimLineWithEllipsis(word, maxCharsPerLine));
      current = "";
    }

    if (lines.length === maxLines) {
      break;
    }
  }

  if (lines.length < maxLines && current) {
    lines.push(current);
  }

  const usedWords = lines.join(" ").split(/\s+/).filter(Boolean).length;
  if (lines.length === maxLines && usedWords < words.length) {
    const lastIndex = maxLines - 1;
    lines[lastIndex] = trimLineWithEllipsis(lines[lastIndex], maxCharsPerLine);
    if (!lines[lastIndex].endsWith("…")) {
      lines[lastIndex] = `${lines[lastIndex].trimEnd()}…`;
    }
  }

  return lines.slice(0, maxLines);
}

function getZoneTextLayout(zoneWidth: number) {
  const innerWidth = zoneWidth - 4.8;
  return {
    innerWidth,
    titleChars: Math.max(9, Math.floor(innerWidth * 1.02)),
    descriptionChars: Math.max(10, Math.floor(innerWidth * 0.9)),
  };
}

type VisualAssetPosition = {
  x: number;
  y: number;
  labelY: number;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getVisualAssetPosition(asset: AssetNode, zone: Zone): VisualAssetPosition {
  const minY = zone.y + NODE_MIN_Y_OFFSET;
  const maxY = zone.y + zone.height - NODE_BOTTOM_INSET;
  const y = clamp(asset.y, minY, maxY);
  const labelY = Math.min(y + NODE_LABEL_OFFSET, zone.y + zone.height - NODE_LABEL_BOTTOM_INSET);

  return {
    x: asset.x,
    y,
    labelY,
  };
}

export function RigSystemsView({ config }: { config: RigTopologyConfig }) {
  const [selectedAssetId, setSelectedAssetId] = useState<string>(config.assets[0]?.id ?? "");
  const [hoveredAssetId, setHoveredAssetId] = useState<string | null>(null);

  const selectedAsset = useMemo(
    () => config.assets.find((asset) => asset.id === selectedAssetId) ?? config.assets[0],
    [config.assets, selectedAssetId],
  );

  const hoveredAsset = hoveredAssetId
    ? config.assets.find((asset) => asset.id === hoveredAssetId) ?? null
    : null;

  const zoneMap = useMemo(
    () => new Map(config.zones.map((zone) => [zone.id, zone])),
    [config.zones],
  );

  const visualAssetMap = useMemo(() => {
    const map = new Map<string, VisualAssetPosition>();

    for (const asset of config.assets) {
      const zone = zoneMap.get(asset.zoneId);
      map.set(
        asset.id,
        zone
          ? getVisualAssetPosition(asset, zone)
          : {
              x: asset.x,
              y: asset.y,
              labelY: asset.y + NODE_LABEL_OFFSET,
            },
      );
    }

    return map;
  }, [config.assets, zoneMap]);

  const stats = topologyStats(config);

  return (
    <section className="dashboard-card dashboard-card-strong p-5">
      <div className="flex flex-col gap-3.5 border-b border-[rgba(120,160,255,0.08)] pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="dashboard-eyebrow">Rig Systems View</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Asset Topology</h3>
          <p className="mt-1.5 text-sm text-mist/64">{config.viewLabel ?? "System layout by operating zone"}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.78)] px-4 py-3">
          <p className="dashboard-meta text-mist/42">Rig</p>
          <p className="mt-1 text-sm font-semibold text-white">{config.rigName}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] px-4 py-3">
          <p className="dashboard-meta text-mist/42">Total assets</p>
          <p className="mt-2 text-2xl font-semibold text-white">{stats.total}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] px-4 py-3">
          <p className="dashboard-meta text-mist/42">Active excursions</p>
          <p className="mt-2 text-2xl font-semibold text-warning">{stats.active}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] px-4 py-3">
          <p className="dashboard-meta text-mist/42">Trip-risk assets</p>
          <p className="mt-2 text-2xl font-semibold text-ember">{stats.critical}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_228px]">
        <div className="relative overflow-hidden rounded-[24px] border border-[rgba(120,160,255,0.08)] bg-[rgba(8,12,20,0.94)] p-3 sm:p-4">
          <div className="pointer-events-none absolute inset-0 bg-grid bg-[size:34px_34px] opacity-[0.05]" />
          <div className="pointer-events-none absolute inset-x-10 top-0 h-28 bg-gradient-to-b from-signal/6 to-transparent" />

          <div className="relative aspect-[1.38/1] w-full">
            <svg viewBox="0 0 100 86" className="h-full w-full" role="img" aria-label={`${config.rigName} system topology`}>
              <g transform={`translate(${TOPOLOGY_TRANSLATE_X} ${TOPOLOGY_TRANSLATE_Y}) scale(${TOPOLOGY_SCALE})`}>
              {config.links?.map((link) => {
                const from = visualAssetMap.get(link.fromAssetId);
                const to = visualAssetMap.get(link.toAssetId);
                if (!from || !to) return null;

                return (
                  <line
                    key={link.id}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke="rgba(120,160,255,0.18)"
                    strokeWidth="0.5"
                    strokeDasharray="2 2"
                  />
                );
              })}

              {config.zones.map((zone) => (
                <g key={zone.id}>
                  {(() => {
                    const { titleChars, descriptionChars } = getZoneTextLayout(zone.width);
                    const title = truncateZoneTitle(zone.label, titleChars);
                    const descriptionLines = zone.description
                      ? wrapZoneDescription(zone.description, descriptionChars, 2)
                      : [];

                    return (
                      <>
                  <rect
                    x={zone.x}
                    y={zone.y}
                    width={zone.width}
                    height={zone.height}
                    rx="4"
                    fill="rgba(15,23,38,0.78)"
                    stroke="rgba(120,160,255,0.12)"
                    strokeWidth="0.45"
                  />
                  <text
                    x={zone.x + 2.4}
                    y={zone.y + 4.3}
                    fontSize="2.9"
                    fontWeight="700"
                    fill="rgba(243,247,250,0.94)"
                    fontFamily="var(--font-sans)"
                  >
                    {title}
                  </text>
                  {descriptionLines.map((line, index) => (
                        <text
                          key={`${zone.id}-desc-${index}`}
                          x={zone.x + 2.4}
                          y={zone.y + 7.4 + index * 2.1}
                          fontSize="1.65"
                          fontWeight="500"
                          fill="rgba(148,163,184,0.72)"
                          fontFamily="var(--font-sans)"
                        >
                          {line}
                        </text>
                      ))}
                      </>
                    );
                  })()}
                </g>
              ))}

              {config.assets.map((asset) => {
                const style = statusStyles[asset.status];
                const isSelected = selectedAsset?.id === asset.id;
                const isHovered = hoveredAssetId === asset.id;
                const radius = isSelected ? SELECTED_NODE_RADIUS : NODE_RADIUS;
                const visual = visualAssetMap.get(asset.id) ?? {
                  x: asset.x,
                  y: asset.y,
                  labelY: asset.y + NODE_LABEL_OFFSET,
                };

                return (
                  <g key={asset.id}>
                    {asset.status === "critical" ? (
                      <circle
                        cx={visual.x}
                        cy={visual.y}
                        r="2.9"
                        fill={style.ring}
                        className="rig-critical-ring origin-center"
                      />
                    ) : null}
                    <foreignObject x={visual.x - 5} y={visual.y - 5} width="10" height="10">
                      <button
                        type="button"
                        aria-label={`${asset.label}, ${formatStatus(asset.status)}`}
                        onClick={() => setSelectedAssetId(asset.id)}
                        onFocus={() => setHoveredAssetId(asset.id)}
                        onBlur={() => setHoveredAssetId(null)}
                        onMouseEnter={() => setHoveredAssetId(asset.id)}
                        onMouseLeave={() => setHoveredAssetId(null)}
                        className="flex h-full w-full items-center justify-center rounded-full bg-transparent outline-none"
                      >
                        <span
                          className={`block rounded-full transition-transform duration-200 ${isSelected || isHovered ? "scale-110" : ""} ${asset.status === "critical" ? "rig-critical-node" : ""}`}
                          style={{
                            width: `${radius * 2}px`,
                            height: `${radius * 2}px`,
                            backgroundColor: style.dot,
                            boxShadow:
                              asset.status === "critical"
                                ? `0 0 0 1.5px rgba(5,7,11,0.9), 0 0 10px rgba(249,115,22,0.22)`
                                : isSelected
                                  ? `0 0 0 4px ${style.ring}`
                                  : `0 0 0 1.5px rgba(5,7,11,0.9)`,
                          }}
                        />
                      </button>
                    </foreignObject>
                    <text
                      x={visual.x}
                      y={visual.labelY}
                      textAnchor="middle"
                      fill={isSelected ? "rgba(243,247,250,0.96)" : "rgba(148,163,184,0.78)"}
                      fontSize="2"
                      fontFamily="var(--font-mono)"
                      fontWeight={isSelected ? "600" : "500"}
                    >
                      {asset.shortLabel ?? asset.label}
                    </text>
                  </g>
                );
              })}
              </g>
            </svg>

            {hoveredAsset ? (
              <div className="pointer-events-none absolute left-4 top-4 z-10 w-[220px] rounded-2xl border border-[rgba(120,160,255,0.12)] bg-[rgba(11,18,32,0.98)] p-3.5 shadow-[0_18px_36px_rgba(0,0,0,0.42)]">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">{hoveredAsset.label}</p>
                    <p className="dashboard-meta mt-1 text-mist/46">{hoveredAsset.type}</p>
                  </div>
                  <span className={`dashboard-meta rounded-full border px-2 py-1 ${statusStyles[hoveredAsset.status].badge}`}>
                    {formatStatus(hoveredAsset.status)}
                  </span>
                </div>
                <div className="mt-3 space-y-2 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="dashboard-meta text-mist/52">Score</span>
                    <span className="font-mono font-medium text-white">{hoveredAsset.anomalyScore ?? "--"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="dashboard-meta text-mist/52">Reading</span>
                    <span className="font-mono font-medium text-white">{hoveredAsset.metricValue ?? "--"}</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {(["normal", "watch", "warning", "critical", "offline"] as AssetStatus[]).map((status) => (
              <div
                key={status}
                className="dashboard-meta flex items-center gap-2 rounded-full border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] px-3 py-1.5 text-mist/56"
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: statusStyles[status].dot }} />
                <span>{formatStatus(status)}</span>
              </div>
            ))}
          </div>
        </div>

        <aside className="rounded-[24px] border border-[rgba(120,160,255,0.1)] bg-[linear-gradient(180deg,rgba(18,28,44,0.9),rgba(11,18,32,0.84))] p-4">
          <p className="dashboard-meta text-mist/42">Selected asset</p>
          {selectedAsset ? (
            <div className="mt-3">
              <div className="flex items-start justify-between gap-3 border-b border-[rgba(120,160,255,0.08)] pb-3">
                <div>
                  <h4 className="text-[1.02rem] font-semibold text-white">{selectedAsset.label}</h4>
                  <p className="dashboard-meta mt-1 text-mist/54">{selectedAsset.type}</p>
                </div>
                <span className={`dashboard-meta rounded-full border px-2.5 py-1 ${statusStyles[selectedAsset.status].badge}`}>
                  {formatStatus(selectedAsset.status)}
                </span>
              </div>

              <div className="mt-3.5 space-y-2.5">
                <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(11,18,32,0.76)] p-3">
                  <p className="dashboard-meta text-mist/42">Latest reading</p>
                  <p className="font-mono mt-1.5 text-sm font-medium text-white">{selectedAsset.metricValue ?? "--"}</p>
                </div>
                <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(11,18,32,0.76)] p-3">
                  <p className="dashboard-meta text-mist/42">Score</p>
                  <p className="font-mono mt-1.5 text-sm font-medium text-white">{selectedAsset.anomalyScore ?? "--"}</p>
                </div>
                <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(11,18,32,0.76)] p-3">
                  <p className="dashboard-meta text-mist/42">Last updated</p>
                  <p className="font-mono mt-1.5 text-sm font-medium text-white">{selectedAsset.lastUpdated ?? "--"}</p>
                </div>
              </div>
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
