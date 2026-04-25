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

export type SheetSnap = "collapsed" | "half" | "full";

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
  selectedChipId: string | null;
  onSelectChip: (id: string) => void;
  onOpenDetail: (s: Selection) => void;
  onChangeAlternate: (routeId: string) => void;
}

const COLLAPSED_PX = 156;
const HALF_RATIO = 0.45;
const FULL_RATIO = 0.85;
const TAP_THRESHOLD_PX = 6;

function snapHeights(viewportH: number) {
  return {
    collapsed: COLLAPSED_PX,
    half: Math.round(viewportH * HALF_RATIO),
    full: Math.round(viewportH * FULL_RATIO),
  };
}

function nearestSnap(
  height: number,
  heights: ReturnType<typeof snapHeights>,
): SheetSnap {
  const d = (s: SheetSnap) => Math.abs(height - heights[s]);
  let best: SheetSnap = "collapsed";
  if (d("half") < d(best)) best = "half";
  if (d("full") < d(best)) best = "full";
  return best;
}

const NEXT_SNAP: Record<SheetSnap, SheetSnap> = {
  collapsed: "half",
  half: "full",
  full: "collapsed",
};

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
  const [viewportH, setViewportH] = useState(() =>
    typeof window === "undefined" ? 800 : window.innerHeight,
  );
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setViewportH(window.innerHeight);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const heights = useMemo(() => snapHeights(viewportH), [viewportH]);

  const [dragHeight, setDragHeight] = useState<number | null>(null);
  const dragRef = useRef<{
    startY: number;
    startHeight: number;
    moved: boolean;
  } | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  const prevSnap = useRef(snap);
  useEffect(() => {
    if (prevSnap.current === "full" && snap !== "full") {
      scrollRef.current?.scrollTo({ top: 0 });
    }
    prevSnap.current = snap;
  }, [snap]);

  const currentHeight = dragHeight ?? heights[snap];
  const isFull = snap === "full";
  const isCollapsed = snap === "collapsed";

  const handlePointerDown = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
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
      const next = clamp(
        drag.startHeight - deltaY,
        heights.collapsed,
        heights.full,
      );
      setDragHeight(next);
    },
    [heights],
  );

  const endDrag = useCallback(
    (e: ReactPointerEvent<HTMLElement>) => {
      const drag = dragRef.current;
      if (!drag) return;
      dragRef.current = null;
      try {
        (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        /* safe to ignore */
      }

      if (!drag.moved) {
        onSnapChange(NEXT_SNAP[snap]);
        setDragHeight(null);
        return;
      }

      const height = dragHeight ?? drag.startHeight;
      onSnapChange(nearestSnap(height, heights));
      setDragHeight(null);
    },
    [dragHeight, heights, onSnapChange, snap],
  );

  const sortedHotspots = useMemo(
    () => [...hotspots].sort((a, b) => a.km_into_trip - b.km_into_trip),
    [hotspots],
  );

  const showSidebar = snap === "half" || snap === "full";

  return (
    <>
      {/* Backdrop scrim — visible in half and full so user can tap to collapse */}
      <div
        aria-hidden
        onClick={() => onSnapChange("collapsed")}
        className={`fixed inset-0 z-899 bg-ink/40 transition-opacity duration-200 lg:hidden ${
          showSidebar ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <div
        role="dialog"
        aria-label="Trip briefing"
        className="anim-sheet-up fixed inset-x-0 bottom-0 z-900 flex flex-col rounded-t-2xl bg-paper-2 shadow-[0_-12px_40px_rgba(11,31,68,0.25)] lg:hidden"
        style={{
          height: `${currentHeight}px`,
          transition:
            dragHeight !== null
              ? "none"
              : "height 240ms cubic-bezier(0.22, 1, 0.36, 1)",
        }}
      >
        {/* Drag handle + eyebrow */}
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
              onSnapChange(NEXT_SNAP[snap]);
            }
          }}
          className="shrink-0 cursor-grab touch-none select-none px-3 pb-1.5 pt-2 active:cursor-grabbing"
        >
          <div className="mx-auto h-1 w-10 rounded-full bg-ink-4/40" />
          <div className="mt-1.5 flex items-center justify-between">
            <span className="font-mono text-[0.625rem] font-medium uppercase tracking-[0.18em] text-ink-3">
              {isFull ? "Tonight's briefing" : "Nearby risks"}
            </span>
            <Chevron up={isCollapsed} />
          </div>
        </div>

        {/* Collapsed: always-visible summary with count, scrollable chips, See all */}
        {isCollapsed && (
          <CollapsedSummary
            sortedHotspots={sortedHotspots}
            insights={insights}
            selectedChipId={selectedChipId}
            onSelectChip={onSelectChip}
            onOpenDetail={onOpenDetail}
            onExpand={() => onSnapChange("half")}
          />
        )}

        {/* Half / Full: sidebar content. Only full gets internal scroll. */}
        {showSidebar && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div
              ref={scrollRef}
              className={`flex-1 px-4 pb-4 pt-2 sm:px-6 ${
                isFull
                  ? "overflow-y-auto overscroll-contain"
                  : "overflow-hidden"
              }`}
            >
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
 * Collapsed-state summary. Always visible in the peek tray so the
 * sheet never looks empty. Shows a count line, horizontally scrollable
 * chip rail with a trailing fade hint, and a "See all" action.
 */
function CollapsedSummary({
  sortedHotspots,
  insights,
  selectedChipId,
  onSelectChip,
  onOpenDetail,
  onExpand,
}: {
  sortedHotspots: HotspotSummary[];
  insights: CrashInsight[];
  selectedChipId: string | null;
  onSelectChip: (id: string) => void;
  onOpenDetail: (s: Selection) => void;
  onExpand: () => void;
}) {
  const allItems: Array<
    | { kind: "hotspot"; data: HotspotSummary }
    | { kind: "insight"; data: CrashInsight }
  > = [
    ...sortedHotspots.map(
      (h) => ({ kind: "hotspot" as const, data: h }),
    ),
    ...insights.map(
      (ins) => ({ kind: "insight" as const, data: ins }),
    ),
  ];

  return (
    <div className="flex flex-col pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      {/* Count line + "See all" as the primary action */}
      <div className="flex items-center justify-between px-4">
        <span className="text-xs font-medium text-ink-2">
          {sortedHotspots.length > 0
            ? `${sortedHotspots.length} hotspot${sortedHotspots.length !== 1 ? "s" : ""} ahead`
            : "No hotspots on route"}
          {insights.length > 0 && (
            <span className="text-ink-4">
              {" "}· {insights.length} insight{insights.length !== 1 ? "s" : ""}
            </span>
          )}
        </span>
        <button
          type="button"
          onClick={onExpand}
          className="rounded-full bg-accent/10 px-2.5 py-0.5 text-[0.6875rem] font-semibold text-accent transition hover:bg-accent/20 active:scale-95"
        >
          See all ›
        </button>
      </div>

      {/* Horizontally scrollable chip rail with trailing fade hint */}
      <div
        className="relative mt-3"
        style={{
          maskImage:
            "linear-gradient(to right, black calc(100% - 32px), transparent)",
          WebkitMaskImage:
            "linear-gradient(to right, black calc(100% - 32px), transparent)",
        }}
      >
        <div
          className="flex gap-1.5 overflow-x-auto pl-4 pr-8 scrollbar-none"
          style={{ WebkitOverflowScrolling: "touch" }}
        >
          {allItems.map((chip, i) => {
            const id =
              chip.kind === "hotspot"
                ? chip.data.hotspot_id
                : chip.data.insight_id;
            const isSelected = selectedChipId === id;
            const label =
              chip.kind === "hotspot"
                ? chip.data.label
                : chipLabel(chip.data);
            const dot =
              chip.kind === "hotspot"
                ? (chip.data.intensity_ratio ?? 0) >= 2.5
                  ? "bg-alert"
                  : (chip.data.intensity_ratio ?? 0) >= 1.5
                    ? "bg-gold"
                    : "bg-good"
                : "bg-gold-strong";
            return (
              <button
                key={id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => {
                  if (isSelected) onOpenDetail(chip);
                  else onSelectChip(id);
                }}
                className={`anim-chip-pop flex flex-none items-center gap-1.5 rounded-full px-3 py-1.5 text-[0.6875rem] font-medium ring-inset transition active:scale-95 ${
                  isSelected
                    ? "bg-ink-2 text-paper ring-1 ring-ink-2"
                    : "bg-paper-3 text-ink-2 ring-1 ring-rule/60"
                }`}
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    isSelected ? "bg-paper" : dot
                  }`}
                />
                <span className="max-w-[110px] truncate">{label}</span>
              </button>
            );
          })}
        </div>
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
      className={`text-ink-4/50 transition-transform duration-200 ${up ? "rotate-0" : "rotate-180"}`}
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
