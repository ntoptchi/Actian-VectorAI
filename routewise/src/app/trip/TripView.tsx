"use client";

import { useMemo, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

import { BriefingCard } from "~/components/BriefingCard";
import { MobileBottomCard } from "~/components/MobileBottomCard";
import { MobileRiskPreview } from "~/components/MobileRiskPreview";
import {
  MobileRiskSheet,
  type SheetSnap,
} from "~/components/MobileRiskSheet";
import { SidebarSections } from "~/components/SidebarSections";
import type {
  CrashInsight,
  HotspotSummary,
  RouteSegment,
  TripBriefResponse,
} from "~/lib/types";

// Leaflet barfs at SSR; load the map component client-only.
const RouteMap = dynamic(() => import("~/components/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center bg-[#08111f] text-xs uppercase tracking-[0.18em] text-paper/60">
      Loading map…
    </div>
  ),
});

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "segment"; data: RouteSegment }
  | { kind: "insight"; data: CrashInsight }
  | null;

export function TripView({
  brief,
  briefingHref,
}: {
  brief: TripBriefResponse;
  briefingHref: string;
}) {
  const [chosenId, setChosenId] = useState<string | null>(brief.chosen_route_id);
  const [selection, setSelection] = useState<Selection>(null);

  const [calloutDismissed, setCalloutDismissed] = useState(false);
  // Mobile sheet state lives here so the red callout can react to it
  // (fades out when the sheet is expanded to full, preventing the
  // callout from peeking out from behind the sheet edge).
  const [sheetSnap, setSheetSnap] = useState<SheetSnap>("peek");
  // Which chip in the mobile tray is "selected" — drives the preview
  // card above the tray. Null = fall back to the default (first
  // hotspot by km, then first insight). Explicit null selection is
  // not currently exposed in the UI; users always have *some* chip
  // previewed unless both lists are empty.
  const [selectedChipId, setSelectedChipId] = useState<string | null>(null);

  const isChosenShowing = chosenId === brief.chosen_route_id;
  const segments = useMemo(
    () =>
      isChosenShowing ? brief.segments : alternateAsSegments(brief, chosenId),
    [isChosenShowing, brief, chosenId],
  );
  const hotspots = useMemo<HotspotSummary[]>(
    () => (isChosenShowing ? brief.hotspots : []),
    [isChosenShowing, brief.hotspots],
  );
  const insights = useMemo<CrashInsight[]>(
    () => (isChosenShowing ? (brief.insights ?? []) : []),
    [isChosenShowing, brief],
  );

  const banner = brief.conditions_banner;
  const totalMin = useMemo(
    () => Math.round(brief.route.duration_s / 60),
    [brief.route.duration_s],
  );
  const distanceKm = useMemo(
    () => Math.round(brief.route.distance_m / 1000),
    [brief.route.distance_m],
  );

  // Pick the worst hotspot for the *desktop* floating "HIGH RISK ZONE"
  // tag (mockup 2). Mobile has been restructured: the card there is
  // the preview of the currently-selected chip in the tray, not a
  // separate worst-hotspot warning. See activeChip below.
  const worstHotspot = useMemo(() => {
    if (hotspots.length === 0) return null;
    return [...hotspots].sort(
      (a, b) => (b.intensity_ratio ?? 0) - (a.intensity_ratio ?? 0),
    )[0];
  }, [hotspots]);

  // Mobile preview: resolve the effective selected chip. If the user
  // hasn't explicitly selected one, default to the first hotspot by
  // km — that's the "next up" item in the sorted tray — and fall
  // back to the first insight if there are no hotspots.
  const sortedHotspots = useMemo(
    () => [...hotspots].sort((a, b) => a.km_into_trip - b.km_into_trip),
    [hotspots],
  );
  const defaultChipId = useMemo(() => {
    if (sortedHotspots[0]) return sortedHotspots[0].hotspot_id;
    if (insights[0]) return insights[0].insight_id;
    return null;
  }, [sortedHotspots, insights]);
  const activeChipId = selectedChipId ?? defaultChipId;
  const activeChip = useMemo<
    | { kind: "hotspot"; data: HotspotSummary }
    | { kind: "insight"; data: CrashInsight }
    | null
  >(() => {
    if (!activeChipId) return null;
    const h = hotspots.find((x) => x.hotspot_id === activeChipId);
    if (h) return { kind: "hotspot", data: h };
    const i = insights.find((x) => x.insight_id === activeChipId);
    if (i) return { kind: "insight", data: i };
    return null;
  }, [activeChipId, hotspots, insights]);

  const sheetIsFull = sheetSnap === "full";

  return (
    <main className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_28rem]">
      {/* Map */}
      <section className="relative h-dvh lg:h-auto">
        <RouteMap
          segments={segments}
          alternates={brief.alternates}
          chosenRouteId={chosenId}
          hotspots={hotspots}
          stops={brief.fatigue_plan.suggested_stops}
          insights={insights}
          onSegmentClick={(s) => setSelection({ kind: "segment", data: s })}
          onHotspotClick={(h) => setSelection({ kind: "hotspot", data: h })}
          onInsightClick={(i) => setSelection({ kind: "insight", data: i })}
        />

        {/* Top-left "Current View" chip */}
        <div className="pointer-events-none absolute left-2 top-2 z-[1000] max-w-[12rem] rounded-sm bg-paper-2/95 p-2 ring-1 ring-rule shadow-[0_8px_24px_rgba(0,0,0,0.25)] sm:left-4 sm:top-4 sm:max-w-[16rem] sm:p-3">
          <div className="eyebrow">Current View</div>
          <div className="mt-1 font-display text-base font-medium leading-tight text-ink sm:text-lg">
            {distanceKm} km · {totalMin} min
          </div>
          <div className="mt-1 hidden text-xs text-ink-3 sm:block">{banner.summary}</div>
        </div>

        {/* Desktop-only floating "HIGH RISK ZONE" callout. Color +
            label adapt to the real intensity so we don't scream
            "HIGH RISK ZONE" in alert red on a 0.5x stretch (caught
            in QA — that lied about the data and wrecked credibility).
            Hidden entirely when there's nothing to surface so the
            map breathes.

            Mobile has been restructured: the equivalent card there
            is MobileRiskPreview below, which previews the chip the
            user has selected in the tray rather than always showing
            the worst hotspot. */}
        {worstHotspot?.intensity_ratio != null && !calloutDismissed && (() => {
          const calloutTone = calloutToneFor(worstHotspot.intensity_ratio);
          return (
            <div
              // Background is applied inline (not via a Tailwind class)
              // because `bg-gold-strong` was silently failing to paint
              // in some builds — the callout read as fully transparent
              // against the dark map, which killed the entire point of
              // the "HIGH RISK ZONE" flag. Inline style bypasses any
              // JIT/content-scan edge case.
              className="absolute bottom-6 left-1/2 z-[1000] hidden -translate-x-1/2 rounded-sm text-left text-paper shadow-[0_12px_28px_rgba(11,31,68,0.4)] lg:block"
              style={{ backgroundColor: calloutTone.bg }}
            >
              <button
                type="button"
                onPointerDown={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  setCalloutDismissed(true);
                }}
                aria-label="Dismiss"
                className="absolute right-1.5 top-1.5 z-10 grid h-7 w-7 place-items-center rounded-full text-paper/70 transition hover:bg-paper/15 hover:text-paper"
              >
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
                  <path d="M1 1l8 8M9 1l-8 8" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() =>
                  setSelection({ kind: "hotspot", data: worstHotspot })
                }
                className="px-3 py-2 pr-9 transition hover:scale-[1.02] active:scale-95 sm:px-4 sm:py-3 sm:pr-10"
              >
                <div className="flex items-center gap-2">
                  <Triangle />
                  <span className="eyebrow text-paper/80">{calloutTone.label}</span>
                </div>
                <div className="mt-1 text-sm font-medium">
                  {worstHotspot.coaching_line ?? worstHotspot.label}
                </div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="font-display text-2xl font-medium leading-none sm:text-3xl">
                    {worstHotspot.intensity_ratio.toFixed(1)}x
                  </span>
                  <span className="font-mono text-[0.625rem] uppercase tracking-[0.18em] text-paper/80">
                    vs Florida avg
                  </span>
                </div>
              </button>
            </div>
          );
        })()}

        {/* Mobile: selected-chip preview card. Sits directly above
            the tray and renders whichever chip is currently selected
            (or the default first chip if none). Fades out when the
            sheet is expanded to full so the scrim reads cleanly. */}
        {activeChip && !sheetIsFull && (
          <MobileRiskPreview
            item={activeChip}
            onClick={() => {
              // Pass the discriminated union through directly so TS
              // keeps the narrow "hotspot" | "insight" variant —
              // rebuilding the object with `{ kind, data }` widens it.
              setSelection(activeChip);
            }}
          />
        )}

        {/* Mobile draggable sheet — peek shows the risk chip rail,
            full reveals the shared sidebar sections. */}
        <MobileRiskSheet
          brief={brief}
          chosenId={chosenId}
          hotspots={hotspots}
          insights={insights}
          briefingHref={briefingHref}
          snap={sheetSnap}
          onSnapChange={setSheetSnap}
          selectedChipId={activeChipId}
          onSelectChip={setSelectedChipId}
          onOpenDetail={(s) => {
            setSelection(s);
            // Keep selectedChipId in sync when opening detail from
            // the sidebar list, so collapsing back to peek shows the
            // last-interacted item previewed.
            if (s.kind === "hotspot") setSelectedChipId(s.data.hotspot_id);
            if (s.kind === "insight") setSelectedChipId(s.data.insight_id);
            // Collapse the sheet when the user commits to inspecting
            // an item — the detail card stacks above, and the sheet
            // being expanded behind it would trap scrolls.
            setSheetSnap("peek");
          }}
          onChangeAlternate={setChosenId}
        />
      </section>

      {/* Right rail — desktop only */}
      <aside className="hidden lg:flex flex-col border-rule bg-paper-2 lg:min-h-0 lg:overflow-y-auto lg:border-l">
        <div className="flex flex-col gap-5 p-4 sm:gap-6 sm:p-6">
          <header className="flex flex-col gap-2">
            <span className="eyebrow">Safety Briefing</span>
            <h1 className="display text-2xl sm:text-3xl">Tonight&apos;s Route</h1>
          </header>

          <SidebarSections
            brief={brief}
            chosenId={chosenId}
            hotspots={hotspots}
            insights={insights}
            onChangeAlternate={setChosenId}
            onSelect={setSelection}
          />
        </div>


        <Link
          href={briefingHref}
          className="sticky bottom-0 mt-auto border-t border-rule bg-ink py-4 text-center text-sm font-semibold text-paper transition hover:bg-ink-2"
        >
          Open full briefing
        </Link>


      </aside>

      {/* Desktop: side-panel briefing card */}
      {selection && (
        <div className="hidden lg:block">
          <BriefingCard
            subject={selection}
            hotspots={hotspots}
            stops={brief.fatigue_plan.suggested_stops}
            onClose={() => setSelection(null)}
          />
        </div>
      )}

      {/* Mobile: bottom card */}
      {selection && (
        <MobileBottomCard
          subject={selection}
          segments={segments}
          onClose={() => setSelection(null)}
          onNavigate={setSelection}
        />
      )}
    </main>
  );
}

function calloutToneFor(ratio: number): { label: string; bg: string } {
  // Tier the callout to the *actual* intensity so the eyebrow doesn't lie:
  //   >= 2.0x  → "HIGH RISK ZONE" (red-600, hard stop)
  //   >= 1.2x  → "ELEVATED RISK"  (amber-600)
  //   < 1.2x   → "WATCH ZONE"     (slate ink, informational)
  //
  // Raw hex (not Tailwind class names) because the container sets the
  // background via an inline style — Tailwind class interpolation was
  // silently missing in some builds and the callout rendered transparent.
  if (ratio >= 2) return { label: "High Risk Zone", bg: "#dc2626" };
  if (ratio >= 1.2) return { label: "Elevated Risk", bg: "#d97706" };
  return { label: "Watch Zone", bg: "#0f172a" };
}

function Triangle() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 0 L12 11 L0 11 Z" />
    </svg>
  );
}

function alternateAsSegments(
  brief: TripBriefResponse,
  routeId: string | null,
): RouteSegment[] {
  if (!routeId) return brief.segments;
  const alt = brief.alternates.find((a) => a.route_id === routeId);
  if (!alt) return brief.segments;
  return [
    {
      segment_id: `${alt.route_id}_full`,
      polyline: alt.polyline,
      from_km: 0,
      to_km: alt.distance_m / 1000,
      aadt: null,
      speed_limit_mph: null,
      n_crashes: alt.n_crashes,
      intensity_ratio: null,
      risk_band: alt.risk_band,
      top_factors: [],
      night_skewed: false,
    },
  ];
}
