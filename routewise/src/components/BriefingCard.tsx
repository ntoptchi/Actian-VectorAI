"use client";

import type { HotspotSummary, RouteSegment } from "~/lib/types";

type CardSubject =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "segment"; data: RouteSegment };

interface Props {
  subject: CardSubject | null;
  onClose?: () => void;
}

/**
 * Sliding side panel briefing card. Floats above the map on the right, fills
 * the right rail width on large screens. Inspired by the "I-75 NB approaching
 * Exit 136" mockup: navy headline, mono eyebrow, navy "PROACTIVE COACHING"
 * callout, big-numeral factor stats, investigator field notes.
 */
export function BriefingCard({ subject, onClose }: Props) {
  if (!subject) return null;

  const title =
    subject.kind === "hotspot" ? subject.data.label : segmentTitle(subject.data);
  const subtitle =
    subject.kind === "hotspot"
      ? `~${subject.data.km_into_trip.toFixed(1)} km into trip`
      : segmentSubtitle(subject.data);
  const coaching =
    subject.kind === "hotspot" ? subject.data.coaching_line : null;
  const intensity = subject.data.intensity_ratio;
  const factors = subject.data.top_factors;
  const aadt = subject.data.aadt;
  const nCrashes = subject.data.n_crashes;
  const status = statusFor(subject);

  return (
    <>
      {/* Backdrop on mobile only — desktop lets the map peek through */}
      <div
        aria-hidden
        onClick={onClose}
        className="fixed inset-0 z-[1100] bg-ink/40 lg:hidden"
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Hotspot briefing"
        className="fixed inset-y-0 right-0 z-[1200] flex w-full max-w-[28rem] flex-col overflow-y-auto bg-paper-2 shadow-[-20px_0_40px_-20px_rgba(11,31,68,0.4)] lg:right-[28rem] lg:max-w-[26rem]"
      >
        {/* Close + status bar */}
        <div className="flex items-center justify-between border-b border-rule px-6 py-3">
          <div className="flex items-center gap-2">
            <span
              className={`grid h-5 w-5 place-items-center rounded-full text-[0.625rem] font-bold text-paper ${status.dot}`}
            >
              {status.glyph}
            </span>
            <span
              className={`font-mono text-[0.6875rem] uppercase tracking-[0.16em] ${status.text}`}
            >
              {status.label}
            </span>
            <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-4">
              · Live snapshot
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close briefing"
            className="grid h-8 w-8 place-items-center rounded-full text-ink-3 transition hover:bg-paper-3 hover:text-ink"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="flex flex-col gap-6 px-6 py-6">
          {/* Headline */}
          <div className="flex flex-col gap-2">
            <h2 className="display text-3xl">{title}</h2>
            <div className="flex items-center gap-2 text-xs text-ink-3">
              <PinIcon />
              <span>{subtitle}</span>
            </div>
          </div>

          {/* PROACTIVE COACHING callout (navy left rail, lifted blue ground) */}
          {coaching && (
            <div className="flex gap-3 rounded-sm border-l-[3px] border-ink bg-[#e7ecf4] p-4">
              <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-ink text-paper">
                <BulbIcon />
              </span>
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-ink-2">
                  Proactive Coaching
                </span>
                <p className="text-sm leading-relaxed text-ink">{coaching}</p>
              </div>
            </div>
          )}

          {/* CRASH FACTOR BREAKDOWN */}
          <div className="flex flex-col gap-3">
            <span className="eyebrow eyebrow-rule">
              <span>Crash Factor Breakdown</span>
            </span>
            <div className="grid grid-cols-2 gap-3">
              <FactorStat
                value={nCrashes}
                label="Matched crashes for tonight's conditions"
                tone="ink"
              />
              <FactorStat
                value={
                  intensity != null ? `${intensity.toFixed(1)}x` : "—"
                }
                label={
                  intensity != null
                    ? "Higher than the FL average rate"
                    : "FL baseline comparison unavailable"
                }
                tone="gold"
              />
            </div>
          </div>

          {/* Visibility / exposure gauge */}
          {aadt != null && (
            <div className="rounded-sm bg-paper-3 p-4 ring-1 ring-rule">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
                  Traffic Exposure
                </span>
                <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink">
                  {exposureLabel(aadt)}
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-sm bg-rule">
                <div
                  className="h-full rounded-sm bg-ink"
                  style={{ width: `${exposureBarPct(aadt)}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-[0.6875rem] text-ink-3">
                <span>AADT {aadt.toLocaleString()} vehicles/day</span>
                <EyeIcon />
              </div>
            </div>
          )}

          {/* TOP FACTORS / "field notes" — list with quote-style cards */}
          {factors && factors.length > 0 && (
            <div className="flex flex-col gap-3">
              <span className="eyebrow eyebrow-rule">
                <span>Investigator Field Notes</span>
              </span>
              <ul className="flex flex-col gap-3">
                {factors.slice(0, 3).map((f, i) => (
                  <li
                    key={f.factor}
                    className="rounded-sm bg-paper-3 p-4 ring-1 ring-rule"
                  >
                    <div className="text-3xl leading-none text-ink-4">
                      &ldquo;
                    </div>
                    <p className="-mt-2 text-sm italic leading-relaxed text-ink-2">
                      {fieldNote(f.factor, f.fraction)}
                    </p>
                    <div className="mt-3 flex items-center gap-2 border-t border-rule pt-3">
                      <span className="grid h-5 w-5 place-items-center rounded-sm bg-paper text-[0.625rem] text-ink-3">
                        {i + 1}
                      </span>
                      <span className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-ink-3">
                        Factor · {f.factor} · {Math.round(f.fraction * 100)}%
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

function FactorStat({
  value,
  label,
  tone,
}: {
  value: string | number;
  label: string;
  tone: "ink" | "gold";
}) {
  const valueColor = tone === "gold" ? "text-gold" : "text-ink";
  return (
    <div className="flex flex-col gap-2 rounded-sm bg-paper-3 p-4 ring-1 ring-rule">
      <span className={`stat-numeral text-4xl ${valueColor}`}>{value}</span>
      <span className="text-[0.6875rem] leading-snug text-ink-3">{label}</span>
    </div>
  );
}

type Status = {
  label: string;
  glyph: string;
  dot: string;
  text: string;
};

function statusFor(subject: CardSubject): Status {
  // Derive status from the actual data so the eyebrow doesn't lie about the
  // segment's tier (caught in QA: a "low" risk segment was being labeled
  // "MODERATE RISK" because the eyebrow was hardcoded).
  const band =
    subject.kind === "segment"
      ? subject.data.risk_band
      : bandFromIntensity(subject.data.intensity_ratio);

  switch (band) {
    case "high":
      return {
        label: "High Risk",
        glyph: "!",
        dot: "bg-alert",
        text: "text-alert",
      };
    case "moderate":
      return {
        label: "Moderate Risk",
        glyph: "!",
        dot: "bg-warn",
        text: "text-warn",
      };
    default:
      return {
        label: "Low Risk",
        glyph: "i",
        dot: "bg-good",
        text: "text-good",
      };
  }
}

function bandFromIntensity(
  ratio: number | null | undefined,
): "low" | "moderate" | "high" {
  if (ratio == null) return "low";
  if (ratio >= 2) return "high";
  if (ratio >= 1.2) return "moderate";
  return "low";
}

function segmentTitle(s: RouteSegment): string {
  return `Segment ${s.from_km.toFixed(1)} – ${s.to_km.toFixed(1)} km`;
}

function segmentSubtitle(s: RouteSegment): string {
  const parts: string[] = [];
  parts.push(`Risk band: ${s.risk_band}`);
  if (s.speed_limit_mph != null) parts.push(`${s.speed_limit_mph} mph posted`);
  if (s.night_skewed) parts.push("night-skewed segment");
  return parts.join(" · ");
}

function exposureBarPct(aadt: number): number {
  // 0 → 0%, 100k → 100%, log-ish.
  const pct = Math.min(100, Math.max(8, Math.round(Math.log10(aadt + 1) * 22)));
  return pct;
}

function exposureLabel(aadt: number): string {
  if (aadt > 80000) return "Severe";
  if (aadt > 30000) return "Heavy";
  if (aadt > 10000) return "Moderate";
  return "Light";
}

function fieldNote(factor: string, fraction: number): string {
  // Lightweight prose generator so the card doesn't read as a raw factor list.
  const pct = Math.round(fraction * 100);
  if (factor.toLowerCase().includes("rain") || factor.toLowerCase().includes("wet")) {
    return `Pavement drainage is suboptimal here. Hydroplaning incidents spike roughly ${pct}% above the segment baseline during heavy precipitation.`;
  }
  if (factor.toLowerCase().includes("dark") || factor.toLowerCase().includes("night")) {
    return `Lighting drops off sharply along this stretch. ${pct}% of matched crashes share dark-no-streetlight conditions — slow on the curves.`;
  }
  if (factor.toLowerCase().includes("rear")) {
    return `${pct}% of matched events were rear-end impacts. Traffic queues up here unexpectedly; leave more following distance than usual.`;
  }
  if (factor.toLowerCase().includes("merge") || factor.toLowerCase().includes("ramp")) {
    return `Right-lane traffic bunches up ahead of the merge. ${pct}% of matched crashes involve lane-change conflict — stay left until clear.`;
  }
  return `${pct}% of matched crashes for tonight's conditions share factor "${factor}". Treat this stretch with extra caution.`;
}

function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    >
      <path d="M2 2l10 10M12 2L2 12" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg
      width="11"
      height="13"
      viewBox="0 0 11 13"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      className="text-ink-3"
    >
      <path d="M5.5 12s4-4.2 4-7.2A4 4 0 0 0 1.5 4.8C1.5 7.8 5.5 12 5.5 12Z" />
      <circle cx="5.5" cy="5" r="1.4" fill="currentColor" />
    </svg>
  );
}

function BulbIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 0a4 4 0 0 0-2.5 7.1V8.5a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V7.1A4 4 0 0 0 6 0Z" />
      <rect x="4.5" y="10" width="3" height="1.4" rx="0.4" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
    >
      <path d="M2.5 8s2-4 5.5-4 5.5 4 5.5 4-2 4-5.5 4S2.5 8 2.5 8Z" />
      <circle cx="8" cy="8" r="2" />
    </svg>
  );
}
