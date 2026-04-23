"use client";

import type { HotspotSummary, NewsArticle } from "~/lib/types";

type PreviewItem =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "news"; data: NewsArticle };

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
 *   - Eyebrow is the *place name* ("Near Miami"), not a tier label —
 *     the color of the card already conveys severity/intensity.
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

  // News preview — same shape, different fields + severity tone.
  const n = item.data;
  const tone = newsTone(n.severity);
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open article: ${n.headline}`}
      className="fixed inset-x-3 bottom-44 z-[1000] flex flex-col gap-1 rounded-lg px-4 py-2 text-left text-paper shadow-[0_10px_24px_rgba(11,31,68,0.35)] transition active:scale-[0.99] lg:hidden"
      style={{ backgroundColor: tone.bg }}
    >
      <div className="flex items-center gap-2">
        <NewsGlyph />
        <span className="truncate font-mono text-[0.625rem] font-semibold uppercase tracking-[0.18em] text-paper/85">
          {n.publisher}
          {n.publish_date ? ` · ${n.publish_date}` : ""}
        </span>
      </div>
      <p className="line-clamp-2 text-[0.8125rem] leading-snug text-paper/95">
        {n.headline}
      </p>
      <span className="inline-flex w-fit items-center rounded-sm bg-paper/15 px-1.5 py-0.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-paper">
        {tone.label}
      </span>
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

function newsTone(
  severity: NewsArticle["severity"],
): { bg: string; label: string } {
  if (severity === "fatal") return { bg: "#dc2626", label: "Fatal" };
  if (severity === "serious") return { bg: "#d97706", label: "Serious" };
  return { bg: "#0f172a", label: "Report" };
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

function NewsGlyph() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <rect x="2" y="2" width="12" height="12" rx="1.5" />
      <path d="M5 5h6M5 8h6M5 11h3" />
    </svg>
  );
}
