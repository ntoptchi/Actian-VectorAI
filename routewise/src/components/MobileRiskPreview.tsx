"use client";

import type { CrashInsight, HotspotSummary } from "~/lib/types";
import { humanizeFactor } from "~/lib/factors";

type PreviewItem =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "insight"; data: CrashInsight };

interface Props {
  item: PreviewItem;
  onClick: () => void;
}

/**
 * Mobile "selected chip preview" card. Sits directly above the risk
 * tray (peek sheet) with zero gap, so visually it reads as a caption
 * for the currently-selected chip — not a standalone warning.
 *
 * Design rules (from product review):
 *   - Left-aligned type, wider than tall (spans the tray width).
 *   - Eyebrow is the *place name* ("Near Miami") for hotspots or the
 *     primary risk factor for insights — the color of the card already
 *     conveys severity/intensity, so the eyebrow is free to carry
 *     context instead of tier.
 *   - Stat row reads "2.1x vs Florida avg" (not "FL AVG FREQUENCY"),
 *     so the comparison is legible to a non-analyst driver at a
 *     glance.
 *   - Whole card is tappable; it's the select-then-drill-in affordance
 *     from the tray (tap chip = select, tap the preview = open the
 *     full detail sheet).
 */
export function MobileRiskPreview({ item, onClick }: Props) {
  if (item.kind === "hotspot") {
    const h = item.data;
    const tone = hotspotTone(h.intensity_ratio);
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label={`Open details for ${h.label}`}
        // `fixed` (not `absolute`) so the card is viewport-anchored —
        // same reference frame as MobileRiskSheet — and can't drift
        // into the tray when the map <section> reflows due to mobile
        // browser chrome (address bar show/hide with h-dvh).
        //
        // Tray peek height is 132px; card sits at bottom-44 (176px)
        // for a 44px actual gap. Effective visual gap after shadow
        // bleed reads around ~30px — in the 24–32px target band.
        className="fixed inset-x-3 bottom-44 z-[1000] flex flex-col gap-1 rounded-lg px-4 py-2 text-left text-paper shadow-[0_10px_24px_rgba(11,31,68,0.35)] transition active:scale-[0.99] lg:hidden"
        style={{ backgroundColor: tone.bg }}
      >
        <div className="flex items-center gap-2">
          <Triangle />
          <span className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.18em] text-paper/85">
            {h.label}
          </span>
        </div>
        {h.coaching_line && (
          <p className="line-clamp-2 text-[0.8125rem] leading-snug text-paper/95">
            {h.coaching_line}
          </p>
        )}
        {h.intensity_ratio != null && (
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-medium leading-none">
              {h.intensity_ratio.toFixed(1)}x
            </span>
            <span className="text-[0.6875rem] text-paper/80">
              vs Florida avg
            </span>
          </div>
        )}
      </button>
    );
  }

  // Insight preview — same shape, amber "lesson" tone, eyebrow is the
  // dominant risk factor (or publisher when there are no tags).
  const ins = item.data;
  const primary = ins.risk_factors[0];
  const eyebrow = primary
    ? humanizeFactor(primary)
    : ins.source.publisher
      ? ins.source.publisher
      : "Lesson";
  const body = ins.lesson?.trim() || ins.incident_summary?.trim() || ins.headline;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open lesson: ${ins.headline}`}
      className="fixed inset-x-3 bottom-44 z-[1000] flex flex-col gap-1 rounded-lg px-4 py-2 text-left text-paper shadow-[0_10px_24px_rgba(11,31,68,0.35)] transition active:scale-[0.99] lg:hidden"
      style={{ backgroundColor: "#b45309" }}
    >
      <div className="flex items-center gap-2">
        <LessonBulb />
        <span className="truncate font-mono text-[0.625rem] font-semibold uppercase tracking-[0.18em] text-paper/85">
          {eyebrow}
        </span>
      </div>
      <p className="line-clamp-2 text-[0.8125rem] leading-snug text-paper/95">
        {body}
      </p>
      {ins.source.publisher && (
        <span className="inline-flex w-fit items-center rounded-sm bg-paper/15 px-1.5 py-0.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-paper">
          {ins.source.publisher}
          {ins.source.publish_date ? ` · ${ins.source.publish_date}` : ""}
        </span>
      )}
    </button>
  );
}

function hotspotTone(ratio: number | null): { bg: string } {
  // Same tier palette as TripView's desktop callout, but we no longer
  // show tier labels in the card — the color is the tier signal and
  // the eyebrow is the place.
  if (ratio != null && ratio >= 2) return { bg: "#dc2626" };
  if (ratio != null && ratio >= 1.2) return { bg: "#d97706" };
  return { bg: "#0f172a" };
}

function Triangle() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden
    >
      <path d="M6 0 L12 11 L0 11 Z" />
    </svg>
  );
}

function LessonBulb() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden
    >
      <path d="M6 0a4 4 0 0 0-2.5 7.1V8.5a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V7.1A4 4 0 0 0 6 0Z" />
      <rect x="4.5" y="10" width="3" height="1.4" rx="0.4" />
    </svg>
  );
}
