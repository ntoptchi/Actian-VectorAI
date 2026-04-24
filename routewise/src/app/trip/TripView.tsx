"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
import { fetchBrief, fetchRoutes } from "~/lib/client-api";
import { parseDepart } from "~/lib/parse-depart";
import type {
  AlternateSummary,
  CrashInsight,
  HotspotSummary,
  LatLon,
  RouteCandidate,
  RouteSegment,
  TripBriefResponse,
} from "~/lib/types";

const RouteMap = dynamic(() => import("~/components/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="relative grid h-full place-items-center bg-[#08111f]">
      <div className="flex flex-col items-center gap-3">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="animate-pulse">
          <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        <span className="text-xs text-slate-400">Loading map</span>
      </div>
    </div>
  ),
});

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "segment"; data: RouteSegment }
  | { kind: "insight"; data: CrashInsight }
  | null;

type Phase = "init" | "routes" | "complete" | "error";

const EMPTY_BRIEF: TripBriefResponse = {
  trip_id: "",
  route: {
    polyline_geojson: { type: "LineString", coordinates: [] },
    distance_m: 0,
    duration_s: 0,
    departure_iso: new Date().toISOString(),
    arrival_iso: new Date().toISOString(),
  },
  conditions_banner: {
    summary: "",
    weather_segments: [],
    sunset_iso: null,
    dark_drive_minutes: 0,
  },
  fatigue_plan: { total_drive_minutes: 0, suggested_stops: [] },
  sunset_during_trip: false,
  hotspots: [],
  pre_trip_checklist: [],
  chosen_route_id: null,
  alternates: [],
  segments: [],
  insights: [],
};

export function TripView({
  origin,
  destination,
  depart,
  briefingHref,
}: {
  origin: LatLon;
  destination: LatLon;
  depart?: string;
  briefingHref: string;
}) {
  const [phase, setPhase] = useState<Phase>("init");
  const [candidates, setCandidates] = useState<RouteCandidate[]>([]);
  const [brief, setBrief] = useState<TripBriefResponse>(EMPTY_BRIEF);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const req = {
      origin,
      destination,
      timestamp: parseDepart(depart) ?? undefined,
    };

    fetchRoutes(req)
      .then((res) => {
        setCandidates(res.candidates);
        setPhase((p) => (p === "init" ? "routes" : p));
      })
      .catch(() => {
        // routes endpoint failing is non-fatal; brief will still
        // provide alternates when it arrives.
      });

    fetchBrief(req)
      .then((res) => {
        setBrief(res);
        setPhase("complete");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Unknown error");
        setPhase("error");
      });
  }, [origin, destination, depart]);

  // --- derived state (mirrors the original TripView logic) -------

  const [chosenId, setChosenId] = useState<string | null>(null);
  // Sync chosenId when brief arrives with a real chosen_route_id
  useEffect(() => {
    if (brief.chosen_route_id) setChosenId(brief.chosen_route_id);
  }, [brief.chosen_route_id]);

  const [selection, setSelection] = useState<Selection>(null);
  const [calloutDismissed, setCalloutDismissed] = useState(false);
  const [sheetSnap, setSheetSnap] = useState<SheetSnap>("peek");
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

  // During the "routes" phase, show candidates as alternates on the map
  // so the user sees the real OSRM shapes before scoring completes.
  const displayAlternates = useMemo<AlternateSummary[]>(() => {
    if (phase === "complete") return brief.alternates;
    if (candidates.length === 0) return [];
    return candidates.map((c) => ({
      route_id: c.route_id,
      polyline: c.polyline,
      distance_m: c.distance_m,
      duration_s: c.duration_s,
      risk_score: 0,
      risk_band: "low" as const,
      n_crashes: 0,
      minutes_delta_vs_fastest: 0,
      risk_delta_vs_fastest: 0,
      segments: [],
    }));
  }, [phase, brief.alternates, candidates]);

  // During routes phase, pre-select the fastest candidate so polylines render
  const displayChosenId = useMemo(() => {
    if (phase === "complete") return chosenId;
    if (candidates.length > 0) return candidates[0]!.route_id;
    return null;
  }, [phase, chosenId, candidates]);

  const banner = brief.conditions_banner;
  const totalMin = useMemo(() => {
    if (phase !== "complete") {
      const fastest = candidates[0];
      return fastest ? Math.round(fastest.duration_s / 60) : null;
    }
    return Math.round(brief.route.duration_s / 60);
  }, [phase, brief.route.duration_s, candidates]);

  const distanceKm = useMemo(() => {
    if (phase !== "complete") {
      const fastest = candidates[0];
      return fastest ? Math.round(fastest.distance_m / 1000) : null;
    }
    return Math.round(brief.route.distance_m / 1000);
  }, [phase, brief.route.distance_m, candidates]);

  const worstHotspot = useMemo(() => {
    if (hotspots.length === 0) return null;
    return [...hotspots].sort(
      (a, b) => (b.intensity_ratio ?? 0) - (a.intensity_ratio ?? 0),
    )[0];
  }, [hotspots]);

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
  const isLoading = phase === "init" || phase === "routes";

  if (phase === "error") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
        <span className="eyebrow">Briefing unavailable</span>
        <div className="rounded-sm border-l-2 border-alert bg-alert-2/60 px-4 py-3 text-sm text-alert">
          {error}
        </div>
        <p className="text-sm text-ink-3">
          Is the FastAPI backend running on port 8080?
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-sm bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-paper transition hover:bg-ink-2"
        >
          ← Back to home
        </Link>
      </main>
    );
  }

  return (
    <main className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_28rem]">
      {/* Map */}
      <section className="relative h-dvh lg:h-auto">
        <RouteMap
          origin={origin}
          destination={destination}
          segments={segments}
          alternates={displayAlternates}
          chosenRouteId={displayChosenId}
          hotspots={hotspots}
          stops={brief.fatigue_plan.suggested_stops}
          insights={insights}
          onSegmentClick={(s) => setSelection({ kind: "segment", data: s })}
          onHotspotClick={(h) => setSelection({ kind: "hotspot", data: h })}
          onInsightClick={(i) => setSelection({ kind: "insight", data: i })}
          onAlternateClick={setChosenId}
        />

        {/* Loading status pill */}
        {isLoading && (
          <div className="absolute left-1/2 top-4 z-[1100] -translate-x-1/2 sm:top-5">
            <div className="flex items-center gap-2.5 rounded-full bg-ink/90 px-4 py-2 shadow-[0_4px_20px_rgba(0,0,0,0.4)] backdrop-blur-md">
              <LoadingDots />
              <span className="text-xs font-medium tracking-wide text-paper/90">
                {phase === "init" ? "Finding routes…" : "Analyzing safety…"}
              </span>
            </div>
          </div>
        )}

        {/* Top-left "Current View" chip — show once we have distance info */}
        {(distanceKm !== null && totalMin !== null) && (
          <div className="pointer-events-none absolute left-2 top-2 z-[1000] max-w-[12rem] rounded-sm bg-paper-2/95 p-2 ring-1 ring-rule shadow-[0_8px_24px_rgba(0,0,0,0.25)] sm:left-4 sm:top-4 sm:max-w-[16rem] sm:p-3">
            <div className="eyebrow">Current View</div>
            <div className="mt-1 font-display text-base font-medium leading-tight text-ink sm:text-lg">
              {distanceKm} km · {totalMin} min
            </div>
            {phase === "complete" && banner.summary && (
              <div className="mt-1 hidden text-xs text-ink-3 sm:block">{banner.summary}</div>
            )}
          </div>
        )}

        {/* Desktop floating callout */}
        {worstHotspot?.intensity_ratio != null && !calloutDismissed && (() => {
          const calloutTone = calloutToneFor(worstHotspot.intensity_ratio);
          return (
            <div
              className="absolute bottom-6 left-1/2 z-[1000] hidden -translate-x-1/2 rounded-sm text-left text-paper shadow-[0_12px_28px_rgba(11,31,68,0.4)] lg:block"
              style={{ backgroundColor: calloutTone.bg }}
            >
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
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
                className="px-3 py-2 pr-9 transition-colors hover:brightness-110 sm:px-4 sm:py-3 sm:pr-10"
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

        {activeChip && !sheetIsFull && (
          <MobileRiskPreview
            item={activeChip}
            onClick={() => {
              setSelection(activeChip);
            }}
          />
        )}

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
            if (s.kind === "hotspot") setSelectedChipId(s.data.hotspot_id);
            if (s.kind === "insight") setSelectedChipId(s.data.insight_id);
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
            <h1 className="display text-2xl sm:text-3xl">Your Route</h1>
          </header>

          {isLoading ? (
            <SidebarSkeleton phase={phase} />
          ) : (
            <SidebarSections
              brief={brief}
              chosenId={chosenId}
              hotspots={hotspots}
              insights={insights}
              onChangeAlternate={setChosenId}
              onSelect={setSelection}
            />
          )}
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

// --- Loading UI components ------------------------------------------------

function LoadingDots() {
  return (
    <span className="flex items-center gap-[3px]">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="loading-dot inline-block h-1.5 w-1.5 rounded-full bg-paper/80"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

function SidebarSkeleton({ phase }: { phase: Phase }) {
  const bar = "skeleton-shimmer rounded";
  return (
    <div className="flex flex-col gap-6">
      {/* "Recommended Route" header */}
      <div className="flex flex-col gap-2">
        <div className={`${bar} h-4 w-36`} />
        <div className={`${bar} h-3 w-52`} />
      </div>

      {/* Route cards skeleton */}
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="flex overflow-hidden rounded-lg bg-paper-3 ring-1 ring-rule"
          style={{ opacity: 1 - i * 0.15 }}
        >
          <span className={`w-1 self-stretch ${i === 0 ? "bg-ink/20" : "bg-transparent"}`} />
          <div className="flex flex-1 flex-col gap-3 p-4">
            <div className="flex justify-between">
              <div className={`${bar} h-5 w-32`} />
              {i === 0 && <div className={`${bar} h-5 w-24 rounded-full`} />}
            </div>
            <div className="grid grid-cols-2 gap-4 border-t border-rule pt-3">
              <div className="flex flex-col gap-1">
                <div className={`${bar} h-7 w-14`} />
                <div className={`${bar} h-2.5 w-10`} />
              </div>
              <div className="flex flex-col gap-1">
                <div className={`${bar} h-7 w-10`} />
                <div className={`${bar} h-2.5 w-16`} />
              </div>
            </div>
            <div className={`${bar} h-3 w-full`} />
          </div>
        </div>
      ))}

      {/* Hotspots skeleton */}
      {phase === "routes" && (
        <div className="flex flex-col gap-2">
          <div className={`${bar} h-4 w-28`} />
          <div className="flex gap-3 rounded-lg bg-paper-3 p-3 ring-1 ring-rule">
            <div className={`${bar} h-9 w-9 shrink-0 rounded`} />
            <div className="flex flex-1 flex-col gap-1.5">
              <div className={`${bar} h-3.5 w-3/4`} />
              <div className={`${bar} h-3 w-full`} />
              <div className={`${bar} mt-1 h-4 w-16 rounded`} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Helper functions (unchanged from original) --------------------------

function calloutToneFor(ratio: number): { label: string; bg: string } {
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
  if (alt.segments?.length > 0) return alt.segments;
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
