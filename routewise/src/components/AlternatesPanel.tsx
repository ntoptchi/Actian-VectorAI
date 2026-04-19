"use client";

import type { AlternateSummary } from "~/lib/types";

interface Props {
  alternates: AlternateSummary[];
  chosenId: string | null;
  onSelect?: (route_id: string) => void;
}

const ROUTE_NAMES = [
  { name: "The Shield Route", via: "via Coastal Hwy 101" },
  { name: "Direct Link", via: "via Interstate 95" },
  { name: "Business Arterial", via: "via 5th Ave Corridor" },
  { name: "Inland Bypass", via: "via State Route 27" },
  { name: "Coastal Loop", via: "via US-1 N" },
];

function fmtMin(seconds: number): string {
  const total = Math.round(seconds / 60);
  const h = Math.floor(total / 60);
  const m = total % 60;
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

export function AlternatesPanel({ alternates, chosenId, onSelect }: Props) {
  if (alternates.length === 0) {
    return (
      <div className="rounded-sm bg-paper-3 px-3 py-4 text-xs text-ink-3 ring-1 ring-rule">
        No alternates available.
      </div>
    );
  }

  const chosenIdx = alternates.findIndex((a) => a.route_id === chosenId);

  return (
    <ul className="flex flex-col gap-3">
      {alternates.map((a, i) => {
        const isChosen = a.route_id === chosenId;
        const meta = ROUTE_NAMES[i] ?? {
          name: `Alternate ${i + 1}`,
          via: "via local roads",
        };
        const deltaPct = Math.round(a.risk_delta_vs_fastest * 100);
        const isFastest = i === 0;
        const minutesDelta = a.minutes_delta_vs_fastest;
        const isSafest = i === chosenIdx;

        return (
          <li key={a.route_id}>
            <button
              type="button"
              onClick={() => onSelect?.(a.route_id)}
              aria-pressed={isChosen}
              className={`relative flex w-full overflow-hidden rounded-sm bg-paper-3 text-left ring-1 transition ${
                isChosen
                  ? "ring-2 ring-ink"
                  : "ring-rule hover:ring-ink/40"
              }`}
            >
              {/* Left navy rail when chosen — matches mockup 2 */}
              <span
                aria-hidden
                className={`w-1 self-stretch ${
                  isChosen ? "bg-ink" : "bg-transparent"
                }`}
              />

              <div className="flex flex-1 flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-display text-lg font-medium leading-tight text-ink">
                      {meta.name}
                    </div>
                    <div className="text-xs text-ink-3">{meta.via}</div>
                  </div>
                  {isSafest && (
                    <span className="shrink-0 rounded-sm bg-ink px-2 py-1 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-paper">
                      Safest
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-rule pt-3">
                  <Stat
                    label="Time"
                    value={fmtMin(a.duration_s)}
                    sublabel={
                      isFastest
                        ? undefined
                        : `${minutesDelta > 0 ? "+" : ""}${minutesDelta.toFixed(0)} min`
                    }
                  />
                  <Stat
                    label="Risk Delta"
                    value={`${deltaPct > 0 ? "+" : ""}${deltaPct}`}
                    valueSuffix="%"
                    tone={
                      deltaPct < 0
                        ? "good"
                        : deltaPct > 0
                          ? "warn"
                          : "neutral"
                    }
                    sublabel={`${a.n_crashes} matched`}
                  />
                </div>
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
  valueSuffix,
  sublabel,
  tone = "neutral",
}: {
  label: string;
  value: string;
  valueSuffix?: string;
  sublabel?: string;
  tone?: "good" | "warn" | "neutral";
}) {
  const valueColor =
    tone === "good" ? "text-good" : tone === "warn" ? "text-gold" : "text-ink";
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-baseline gap-0.5">
        <span className={`stat-numeral text-2xl ${valueColor}`}>{value}</span>
        {valueSuffix && (
          <span className={`stat-numeral text-base ${valueColor}`}>
            {valueSuffix}
          </span>
        )}
      </div>
      <span className="font-mono text-[0.625rem] uppercase tracking-[0.18em] text-ink-3">
        {label}
      </span>
      {sublabel && (
        <span className="text-[0.6875rem] text-ink-4">{sublabel}</span>
      )}
    </div>
  );
}
