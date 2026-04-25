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

const RISK_LABEL: Record<RiskBand, string> = {
  low: "Low risk",
  moderate: "Moderate",
  elevated: "Elevated",
  high: "High risk",
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

  const recommendedIdx = alternates.findIndex((a) => a.route_id === chosenId);

  return (
    <ul className="flex flex-col gap-2.5">
      {alternates.map((a, i) => {
        const isChosen = a.route_id === chosenId;
        const isFastest = i === 0;
        const minutesDelta = a.minutes_delta_vs_fastest;
        const isRecommended = i === recommendedIdx;
        const matchCaption =
          a.n_crashes === 0
            ? "No crash history matching current conditions."
            : `${a.n_crashes} ${a.n_crashes === 1 ? "segment matches" : "segments match"} current conditions.`;

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
                    label="Matches"
                    value={String(a.n_crashes)}
                    tone={a.n_crashes === 0 ? "good" : "neutral"}
                  />
                  <Stat
                    label="Risk"
                    value={RISK_LABEL[a.risk_band]}
                    tone={
                      a.risk_band === "low"
                        ? "good"
                        : a.risk_band === "high"
                          ? "warn"
                          : "neutral"
                    }
                  />
                </div>

                <p className="text-xs leading-relaxed text-ink-3">
                  {matchCaption}
                </p>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

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
  tone?: "good" | "warn" | "neutral";
  sublabelTone?: "good" | "warn" | "neutral";
}) {
  const valueColor =
    tone === "good" ? "text-good" : tone === "warn" ? "text-gold" : "text-ink";
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
