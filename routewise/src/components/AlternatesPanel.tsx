"use client";

import type { AlternateSummary, RiskBand } from "~/lib/types";

interface Props {
  alternates: AlternateSummary[];
  chosenId: string | null;
  onSelect?: (route_id: string) => void;
}

const RISK_DOT_COLOR: Record<RiskBand, string> = {
  low: "#4ade80",
  moderate: "#fbbf24",
  elevated: "#fb923c",
  high: "#ef4444",
};

function fmtMin(seconds: number): string {
  const total = Math.round(seconds / 60);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

function fmtKm(meters: number): string {
  return `${Math.round(meters / 1000)} km`;
}

export function AlternatesPanel({ alternates, chosenId, onSelect }: Props) {
  if (alternates.length === 0) {
    return (
      <div className="rounded-lg bg-paper-3 px-3 py-4 text-xs text-ink-3 ring-1 ring-rule">
        No alternates available.
      </div>
    );
  }

  const sortedAlternates = [...alternates].sort((a, b) => {
    const aExposure = a.risk_score > 0 ? a.risk_score : Number.POSITIVE_INFINITY;
    const bExposure = b.risk_score > 0 ? b.risk_score : Number.POSITIVE_INFINITY;
    if (aExposure !== bExposure) return aExposure - bExposure;
    return a.duration_s - b.duration_s;
  });
  const recommendedIdx = sortedAlternates.findIndex((a) => a.route_id === chosenId);

  return (
    <ul className="flex flex-col gap-2.5">
      {sortedAlternates.map((a, i) => {
        const isChosen = a.route_id === chosenId;
        const fastestDuration = Math.min(...sortedAlternates.map((x) => x.duration_s));
        const isFastest = a.duration_s === fastestDuration;
        const minutesDelta = a.minutes_delta_vs_fastest;
        const isRecommended = i === recommendedIdx;
        const exposure = a.risk_score;
        const exposureCaption =
          exposure <= 0
            ? "Exposure baseline unavailable for this route."
            : `${exposure.toFixed(2)} crashes/km equivalent under current conditions.`;

        return (
          <li key={a.route_id}>
            <button
              type="button"
              onClick={() => onSelect?.(a.route_id)}
              aria-pressed={isChosen}
              className={`relative flex w-full overflow-hidden rounded-lg bg-paper-3 text-left ring-1 transition duration-150 ${
                isChosen
                  ? "ring-2 ring-ink shadow-sm"
                  : "ring-rule hover:ring-ink/40"
              }`}
            >
              <span
                aria-hidden
                className={`w-1 self-stretch transition-colors ${
                  isChosen ? "bg-ink" : "bg-transparent"
                }`}
              />

              <div className="flex flex-1 flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: RISK_DOT_COLOR[a.risk_band] }}
                    />
                    <span className="text-base font-semibold leading-tight text-ink">
                      Route {i + 1}
                    </span>
                    <span className="text-xs text-ink-4">
                      {fmtKm(a.distance_m)}
                    </span>
                  </div>
                  {!isChosen && isRecommended && (
                    <span className="shrink-0 rounded-full bg-ink px-2.5 py-0.5 text-[0.6875rem] font-semibold text-paper">
                      Recommended
                    </span>
                  )}
                </div>
                <MiniBars segments={a.segments} />

                <div className="grid grid-cols-3 gap-3 border-t border-rule pt-3">
                  <Stat
                    label="Time"
                    value={fmtMin(a.duration_s)}
                    sublabel={
                      isFastest
                        ? "Fastest"
                        : `+${Math.abs(minutesDelta).toFixed(0)} min`
                    }
                    sublabelTone={isFastest ? "good" : "neutral"}
                  />
                  <Stat
                    label="Exposure"
                    value={exposure > 0 ? `${exposure.toFixed(2)}x` : "—"}
                    tone={toneFromExposure(exposure)}
                  />
                  <Stat
                    label="Risk"
                    value={riskLabelFromExposure(exposure)}
                    tone={toneFromExposure(exposure)}
                  />
                </div>

                <p className="text-xs leading-relaxed text-ink-3">
                  {exposureCaption}{" "}
                  <span className="text-ink-4">
                    Drill-down: {a.n_crashes} matched crash{a.n_crashes === 1 ? "" : "es"}.
                  </span>
                </p>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function MiniBars({ segments }: { segments: AlternateSummary["segments"] }) {
  if (!segments || segments.length === 0) return null;
  const buckets = bucketSegments(segments, 12);
  return (
    <div className="space-y-1.5">
      <div className="text-[0.625rem] uppercase tracking-[0.12em] text-ink-3">
        Route profile
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full ring-1 ring-rule">
        {buckets.map((b, idx) => (
          <span
            key={`risk-${idx}`}
            className="flex-1"
            style={{ backgroundColor: RISK_DOT_COLOR[b.riskBand] }}
            title={bucketTooltip(b)}
          />
        ))}
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full ring-1 ring-rule">
        {buckets.map((b, idx) => (
          <span
            key={`traffic-${idx}`}
            className="flex-1"
            style={{ backgroundColor: trafficColorForAadt(b.aadt) }}
            title={bucketTooltip(b)}
          />
        ))}
      </div>
    </div>
  );
}

function riskLabelFromExposure(exposure: number): string {
  if (exposure <= 0) return "Unknown";
  if (exposure < 1.1) return "Low";
  if (exposure < 1.6) return "Moderate";
  if (exposure < 2.2) return "Elevated";
  return "High";
}

function riskColorFromExposure(exposure: number): string {
  if (exposure <= 0) return "#94a3b8";
  if (exposure < 1.1) return "#4ade80";
  if (exposure < 1.6) return "#eab308";
  if (exposure < 2.2) return "#f97316";
  return "#ef4444";
}

function toneFromExposure(exposure: number): StatTone {
  if (exposure <= 0) return "neutral";
  if (exposure < 1.1) return "good";
  if (exposure < 1.6) return "moderate";
  if (exposure < 2.2) return "elevated";
  return "warn";
}

function trafficColorForAadt(aadt: number | null): string {
  if (aadt == null) return "#cbd5e1";
  if (aadt >= 80000) return "#0f172a";
  if (aadt >= 40000) return "#334155";
  if (aadt >= 18000) return "#64748b";
  return "#94a3b8";
}

function trafficLabelFromAadt(aadt: number | null): string {
  if (aadt == null) return "Unknown";
  if (aadt >= 80000) return "Heavy";
  if (aadt >= 40000) return "Busy";
  if (aadt >= 18000) return "Moderate";
  return "Light";
}

function bucketSegments(segments: AlternateSummary["segments"], bucketCount: number) {
  const totalKm = Math.max(segments[segments.length - 1]?.to_km ?? 1, 1);
  const out = Array.from({ length: bucketCount }, (_, idx) => {
    const start = (idx / bucketCount) * totalKm;
    const end = ((idx + 1) / bucketCount) * totalKm;
    const overlaps = segments
      .map((seg) => ({
        seg,
        overlap: Math.max(0, Math.min(end, seg.to_km) - Math.max(start, seg.from_km)),
      }))
      .filter((item) => item.overlap > 0);
    const relevant =
      overlaps.length > 0
        ? overlaps
        : [
            {
              seg: segments[Math.min(idx, segments.length - 1)]!,
              overlap: end - start,
            },
          ];
    const totalOverlap = relevant.reduce((sum, item) => sum + item.overlap, 0) || 1;
    const dominant = [...relevant].sort((a, b) => b.overlap - a.overlap)[0]!;
    return {
      fromKm: start,
      toKm: end,
      exposure: relevant.reduce(
        (sum, item) => sum + item.overlap * effectiveExposure(item.seg),
        0,
      ) / totalOverlap,
      aadt:
        relevant.reduce(
          (sum, item) => sum + item.overlap * (item.seg.aadt ?? 0),
          0,
        ) / totalOverlap || null,
      riskBand: dominant.seg.risk_band,
    };
  });
  return out;
}

function bucketTooltip(b: {
  fromKm: number;
  toKm: number;
  exposure: number;
  aadt: number | null;
  riskBand: RiskBand;
}) {
  return `${b.fromKm.toFixed(0)}-${b.toKm.toFixed(0)} km · Risk ${RISK_LABEL(
    b.riskBand,
  )} · Traffic ${trafficLabelFromAadt(b.aadt)} · Exposure ${
    b.exposure > 0 ? `${b.exposure.toFixed(2)}x` : "N/A"
  }`;
}

function effectiveExposure(seg: AlternateSummary["segments"][number]): number {
  return (
    seg.exposure_intensity_ratio ??
    (seg.risk_band === "high"
      ? 2.3
      : seg.risk_band === "elevated"
        ? 1.8
        : seg.risk_band === "moderate"
          ? 1.3
          : 0.9)
  );
}

function RISK_LABEL(band: RiskBand): string {
  if (band === "moderate") return "Moderate";
  if (band === "elevated") return "Elevated";
  if (band === "high") return "High";
  return "Low";
}

type StatTone = "good" | "warn" | "neutral" | "moderate" | "elevated";

function Stat({
  label,
  value,
  sublabel,
  tone = "neutral",
  sublabelTone = "neutral",
}: {
  label: string;
  value: string;
  sublabel?: string;
  tone?: StatTone;
  sublabelTone?: StatTone;
}) {
  const valueColor =
    tone === "good"
      ? "text-good"
      : tone === "warn"
        ? "text-red-500"
        : tone === "elevated"
          ? "text-orange-500"
          : tone === "moderate"
            ? "text-yellow-500"
            : "text-ink";
  const subColor =
    sublabelTone === "good" ? "text-good" : "text-ink-4";
  return (
    <div className="flex flex-col gap-0.5">
      <span className={`font-display text-lg font-semibold leading-tight ${valueColor}`}>
        {value}
      </span>
      <span className="text-[0.625rem] text-ink-3">
        {label}
      </span>
      {sublabel && (
        <span className={`text-[0.6875rem] ${subColor}`}>{sublabel}</span>
      )}
    </div>
  );
}
