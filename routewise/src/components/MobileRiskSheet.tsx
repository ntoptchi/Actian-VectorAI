"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import type {
  CrashInsight,
  HotspotSummary,
  LessonZone,
  NewsCrashPin,
  TripBriefResponse,
} from "~/lib/types";
import { SidebarSections } from "./SidebarSections";

export type SheetSnap = "peek" | "full";

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "insight"; data: CrashInsight }
  | { kind: "lesson_zone"; data: LessonZone }
  | { kind: "news_crash"; data: NewsCrashPin };

interface Props {
  brief: TripBriefResponse;
  chosenId: string | null;
  hotspots: HotspotSummary[];
  insights: CrashInsight[];
  lessonZones: LessonZone[];
  newsCrashes: NewsCrashPin[];
  briefingHref: string;
  snap: SheetSnap;
  onSnapChange: (snap: SheetSnap) => void;
  // Peek-rail chip interactions — tap to *select* (update the preview
  // card above the tray); tap-again on the already-selected chip to
  // *open detail* (MobileBottomCard). The selectedChipId is the
  // hotspot_id or insight_id of the currently-previewed item.
  selectedChipId: string | null;
  onSelectChip: (id: string) => void;
  // Open the full detail sheet. Called from the sidebar list rows in
  // full state, and from tap-again on an already-selected peek chip.
  onOpenDetail: (s: Selection) => void;
  onChangeAlternate: (routeId: string) => void;
}

/**
 * Peek height in px. Generous enough to fit:
 *   - drag handle strip (~28px)
 *   - eyebrow row (~18px)
 *   - chip row (~36px)
 *   - safe-area padding on notch phones (~34px)
 * On non-notch devices there's a little extra breathing room at the
 * bottom of the peek sheet, which reads as intentional padding and
 * keeps the chips comfortably above the home-indicator area.
 */
const PEEK_PX = 132;

/**
 * Movement threshold (in px) that distinguishes a tap from a drag.
 * Anything under this and we treat the pointerup as a tap — which
 * toggles snaps instead of snapping by position.
 */
const TAP_THRESHOLD_PX = 6;

/**
 * Mobile draggable bottom sheet that gives mobile parity with the
 * desktop right rail.
 *
 *   peek: shows today's "Nearby risks" chip selector.
 *   full: scrollable panel with alternates / hotspots / news / stops
 *         and a sticky "Open full briefing" footer link.
 *
 * The handle strip at the top is both a drag target (pointer events)
 * and a tap target (toggle snaps). Dragging past the midpoint snaps
 * to the nearer of the two positions on release; a non-drag tap
 * toggles. A backdrop scrim fades in while the sheet is expanded so
 * the map recedes and the sheet reads as a modal-over-map (tap to
 * collapse).
 */
export function MobileRiskSheet({
  brief,
  chosenId,
  hotspots,
  insights,
  lessonZones,
  newsCrashes,
  briefingHref,
  snap,
  onSnapChange,
  selectedChipId,
  onSelectChip,
  onOpenDetail,
  onChangeAlternate,
}: Props) {
  // We track viewport height because "full" is a percentage of it.
  // Using state + resize listener (rather than reading every render)
  // keeps the sheet responsive to rotation / keyboard show-hide.
  const [viewportH, setViewportH] = useState(() =>
    typeof window === "undefined" ? 800 : window.innerHeight,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setViewportH(window.innerHeight);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const fullPx = Math.round(viewportH * 0.85);

  // Active drag height. When null, the sheet height comes from the
  // snap prop (and transitions smoothly). When dragging, we write
  // the live height into this state and disable the CSS transition.
  const [dragHeight, setDragHeight] = useState<number | null>(null);
  const dragRef = useRef<{
    startY: number;
    startHeight: number;
    moved: boolean;
  } | null>(null);

  const currentHeight =
    dragHeight ?? (snap === "peek" ? PEEK_PX : fullPx);
  const isFull = snap === "full";

  const handlePointerDown = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
      // Only capture primary-button pointers — right-clicks and
      // two-finger touches shouldn't initiate a drag.
      if (e.button !== 0 && e.pointerType === "mouse") return;
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      dragRef.current = {
        startY: e.clientY,
        startHeight: currentHeight,
        moved: false,
      };
      setDragHeight(currentHeight);
    },
    [currentHeight],
  );

  const handlePointerMove = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
      const drag = dragRef.current;
      if (!drag) return;
      const deltaY = e.clientY - drag.startY;
      if (!drag.moved && Math.abs(deltaY) > TAP_THRESHOLD_PX) {
        drag.moved = true;
      }
      const next = clamp(drag.startHeight - deltaY, PEEK_PX, fullPx);
      setDragHeight(next);
    },
    [fullPx],
  );

  const endDrag = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
      const drag = dragRef.current;
      if (!drag) return;
      dragRef.current = null;
      try {
        (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Safe to ignore — older browsers may throw if not captured.
      }

      if (!drag.moved) {
        // A tap toggles snaps.
        onSnapChange(snap === "peek" ? "full" : "peek");
        setDragHeight(null);
        return;
      }

      // Snap to whichever point the current height is closer to.
      const height = dragHeight ?? drag.startHeight;
      const mid = (PEEK_PX + fullPx) / 2;
      onSnapChange(height > mid ? "full" : "peek");
      setDragHeight(null);
    },
    [dragHeight, fullPx, onSnapChange, snap],
  );

  const sortedHotspots = useMemo(
    () => [...hotspots].sort((a, b) => a.km_into_trip - b.km_into_trip),
    [hotspots],
  );

  return (
    <>
      {/* Backdrop scrim — only interactive in full state so it doesn't
          steal taps from the map when the sheet is collapsed. */}
      <div
        aria-hidden
        onClick={() => onSnapChange("peek")}
        className={`fixed inset-0 z-[899] bg-ink/40 transition-opacity duration-200 lg:hidden ${
          isFull ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <div
        role="dialog"
        aria-label="Trip briefing"
        aria-expanded={isFull}
        className="anim-sheet-up fixed inset-x-0 bottom-0 z-[900] flex flex-col rounded-t-2xl bg-paper-2 shadow-[0_-12px_40px_rgba(11,31,68,0.25)] lg:hidden"
        style={{
          height: `${currentHeight}px`,
          transition:
            dragHeight !== null
              ? "none"
              : "height 240ms cubic-bezier(0.22, 1, 0.36, 1)",
        }}
      >
        {/* Drag handle + eyebrow — the whole strip is the drag/tap
            target. `touch-none` prevents the browser from hijacking
            the pointer for native scroll/zoom during a drag. */}
        <div
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          role="button"
          tabIndex={0}
          aria-label={isFull ? "Collapse briefing" : "Expand briefing"}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSnapChange(isFull ? "peek" : "full");
            }
          }}
          className="shrink-0 cursor-grab touch-none select-none px-3 pb-1.5 pt-2 active:cursor-grabbing"
        >
          <div className="mx-auto h-1 w-10 rounded-full bg-ink-4/40" />
          <div className="mt-1.5 flex items-center justify-between">
            <span className="font-mono text-[0.625rem] font-medium uppercase tracking-[0.18em] text-ink-3">
              {isFull ? "Tonight's briefing" : "Nearby risks"}
            </span>
            <Chevron up={!isFull} />
          </div>
        </div>

        {/* Peek: compact risk rail. Hidden when full so the
            container doesn't briefly render both states. */}
        {!isFull && (
          <PeekRail
            sortedHotspots={sortedHotspots}
            insights={insights}
            briefingHref={briefingHref}
            selectedChipId={selectedChipId}
            onSelectChip={onSelectChip}
            onOpenDetail={onOpenDetail}
          />
        )}

        {/* Full: scrollable sidebar content + sticky footer link.
            `overscroll-contain` stops rubber-banding from bleeding
            through to the page behind (important on iOS). */}
        {isFull && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-4 pt-2 sm:px-6">
              <div className="flex flex-col gap-5 sm:gap-6">
                <SidebarSections
                  brief={brief}
                  chosenId={chosenId}
                  hotspots={hotspots}
                  lessonZones={lessonZones}
                  insights={insights}
                  newsCrashes={newsCrashes}
                  onChangeAlternate={onChangeAlternate}
                  onSelect={onOpenDetail}
                />
              </div>
            </div>
            <Link
              href={briefingHref}
              className="shrink-0 border-t border-rule bg-ink py-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-center text-sm font-semibold text-paper transition hover:bg-ink-2"
            >
              Open full briefing
            </Link>
          </div>
        )}
      </div>
    </>
  );
}

/**
 * Peek-state chip rail. Each chip is a risk item (hotspot or insight);
 * tapping selects it (drives the preview card above the tray), and
 * tapping an already-selected chip opens the full detail sheet —
 * the same "tap again to drill in" pattern iOS tab bars use.
 *
 * Selected chips get a filled ink pill treatment so the link between
 * "this chip is selected" and "this is the card's subject" is
 * visually unambiguous.
 */
function PeekRail({
  sortedHotspots,
  insights,
  briefingHref,
  selectedChipId,
  onSelectChip,
  onOpenDetail,
}: {
  sortedHotspots: HotspotSummary[];
  insights: CrashInsight[];
  briefingHref: string;
  selectedChipId: string | null;
  onSelectChip: (id: string) => void;
  onOpenDetail: (s: Selection) => void;
}) {
  let chipIndex = 0;
  return (
    <div className="pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <div
        className="flex gap-1.5 overflow-x-auto px-3 pt-1 scrollbar-none"
        style={{ WebkitOverflowScrolling: "touch" }}
      >
        {sortedHotspots.map((h) => {
          const isSelected = selectedChipId === h.hotspot_id;
          const dot =
            (h.intensity_ratio ?? 0) >= 2.5
              ? "bg-alert"
              : (h.intensity_ratio ?? 0) >= 1.5
                ? "bg-gold"
                : "bg-good";
          const delay = chipIndex * 60;
          chipIndex++;
          return (
            <button
              key={h.hotspot_id}
              type="button"
              aria-pressed={isSelected}
              onClick={() => {
                if (isSelected) {
                  onOpenDetail({ kind: "hotspot", data: h });
                } else {
                  onSelectChip(h.hotspot_id);
                }
              }}
              className={`anim-chip-pop flex flex-none items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.6875rem] font-medium ring-inset transition active:scale-95 ${
                isSelected
                  ? "bg-ink-2 text-paper ring-1 ring-ink-2"
                  : "bg-paper-3 text-ink-2 ring-1 ring-rule/60"
              }`}
              style={{ animationDelay: `${delay}ms` }}
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                  isSelected ? "bg-paper" : dot
                }`}
              />
              <span className="max-w-[110px] truncate">{h.label}</span>
              <span
                className={`font-mono text-[0.625rem] font-medium tracking-wide ${
                  isSelected ? "text-paper/75" : "text-ink-4"
                }`}
              >
                {h.km_into_trip.toFixed(0)}km
              </span>
            </button>
          );
        })}

        {insights.map((ins) => {
          const isSelected = selectedChipId === ins.insight_id;
          const delay = chipIndex * 60;
          chipIndex++;
          // Chip body shows a trimmed incident summary — the same
          // "what happened" one-liner used in the sidebar InsightRow,
          // so the two surfaces don't read differently.
          const label = chipLabel(ins);
          return (
            <button
              key={ins.insight_id}
              type="button"
              aria-pressed={isSelected}
              onClick={() => {
                if (isSelected) {
                  onOpenDetail({ kind: "insight", data: ins });
                } else {
                  onSelectChip(ins.insight_id);
                }
              }}
              className={`anim-chip-pop flex flex-none items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.6875rem] font-medium ring-inset transition active:scale-95 ${
                isSelected
                  ? "bg-ink-2 text-paper ring-1 ring-ink-2"
                  : "bg-paper-3 text-ink-2 ring-1 ring-rule/60"
              }`}
              style={{ animationDelay: `${delay}ms` }}
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                  isSelected ? "bg-paper" : "bg-gold-strong"
                }`}
              />
              <span className="max-w-[110px] truncate">{label}</span>
            </button>
          );
        })}

        <Link
          href={briefingHref}
          className="anim-chip-pop flex flex-none items-center gap-1.5 rounded-full bg-ink-2 px-3 py-1.5 text-[0.6875rem] font-medium uppercase tracking-[0.12em] text-paper active:scale-95"
          style={{ animationDelay: `${chipIndex * 60}ms` }}
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          >
            <rect x="3" y="2" width="10" height="12" rx="1.5" />
            <path d="M6 5h4M6 8h4M6 11h2" />
          </svg>
          Full briefing
        </Link>
      </div>
    </div>
  );
}

function Chevron({ up }: { up: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`text-ink-3 transition-transform duration-200 ${up ? "rotate-0" : "rotate-180"}`}
      aria-hidden
    >
      <path d="M4 10l4-4 4 4" />
    </svg>
  );
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}

/**
 * Short chip label for an insight. Prefers a trimmed headline, falling
 * back to the first risk factor or a generic "Lesson" so the chip
 * never renders blank even for sparsely-tagged insights.
 */
function chipLabel(ins: CrashInsight): string {
  const h = (ins.headline || "").trim();
  if (h) return h.length > 40 ? h.slice(0, 40).replace(/\s\S*$/, "") + "…" : h;
  if (ins.risk_factors[0]) return ins.risk_factors[0].replace(/_/g, " ");
  return "Lesson";
}
