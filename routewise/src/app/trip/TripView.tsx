"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";

import { AlternatesPanel } from "~/components/AlternatesPanel";
import { BriefingCard } from "~/components/BriefingCard";
import type {
  HotspotSummary,
  NewsArticle,
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
  | { kind: "news"; data: NewsArticle }
  | null;

export function TripView({ brief }: { brief: TripBriefResponse }) {
  const [chosenId, setChosenId] = useState<string | null>(brief.chosen_route_id);
  const [selection, setSelection] = useState<Selection>(null);

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
  const newsArticles = useMemo<NewsArticle[]>(
    () => (isChosenShowing ? (brief.news_articles ?? []) : []),
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

  // Pick the worst hotspot for the floating "HIGH RISK ZONE" tag (mockup 2).
  const worstHotspot = useMemo(() => {
    if (hotspots.length === 0) return null;
    return [...hotspots].sort(
      (a, b) => (b.intensity_ratio ?? 0) - (a.intensity_ratio ?? 0),
    )[0];
  }, [hotspots]);

  return (
    <main className="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_28rem]">
      {/* Map */}
      <section className="relative h-[55vh] min-h-0 lg:h-auto">
        <RouteMap
          segments={segments}
          alternates={brief.alternates}
          chosenRouteId={chosenId}
          hotspots={hotspots}
          newsArticles={newsArticles}
          onSegmentClick={(s) => setSelection({ kind: "segment", data: s })}
          onHotspotClick={(h) => setSelection({ kind: "hotspot", data: h })}
          onNewsClick={(n) => setSelection({ kind: "news", data: n })}
        />

        {/* Top-left "Current View" chip */}
        <div className="pointer-events-none absolute left-4 top-4 z-[1000] max-w-[16rem] rounded-sm bg-paper-2/95 p-3 ring-1 ring-rule shadow-[0_8px_24px_rgba(0,0,0,0.25)]">
          <div className="eyebrow">Current View</div>
          <div className="mt-1 font-display text-lg font-medium leading-tight text-ink">
            {distanceKm} km · {totalMin} min
          </div>
          <div className="mt-1 text-xs text-ink-3">{banner.summary}</div>
        </div>

        {/* Floating callout near the worst hotspot — color + label adapt to
            the real intensity so we don't scream "HIGH RISK ZONE" in alert
            red on a 0.5x stretch (caught in QA — that lied about the data
            and wrecked credibility). Hidden entirely when there's nothing
            to surface so the map breathes. */}
        {worstHotspot?.intensity_ratio != null && (() => {
          const calloutTone = calloutToneFor(worstHotspot.intensity_ratio);
          return (
            <button
              type="button"
              onClick={() =>
                setSelection({ kind: "hotspot", data: worstHotspot })
              }
              className={`absolute bottom-6 left-1/2 z-[1000] -translate-x-1/2 rounded-sm px-4 py-3 text-left text-paper shadow-[0_12px_28px_rgba(11,31,68,0.4)] transition hover:scale-[1.02] ${calloutTone.bg}`}
            >
              <div className="flex items-center gap-2">
                <Triangle />
                <span className="eyebrow text-paper/80">{calloutTone.label}</span>
              </div>
              <div className="mt-1 text-sm font-medium">
                {worstHotspot.coaching_line ?? worstHotspot.label}
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-display text-3xl font-medium leading-none">
                  {worstHotspot.intensity_ratio.toFixed(1)}x
                </span>
                <span className="font-mono text-[0.625rem] uppercase tracking-[0.18em] text-paper/80">
                  FL avg frequency
                </span>
              </div>
            </button>
          );
        })()}
      </section>

      {/* Right rail */}
      <aside className="flex flex-col border-rule bg-paper-2 lg:min-h-0 lg:overflow-y-auto lg:border-l">
        <div className="flex flex-col gap-6 p-6">
          <header className="flex flex-col gap-2">
            <span className="eyebrow">Safety Briefing</span>
            <h1 className="display text-3xl">Route Analysis</h1>
          </header>

          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-base font-semibold text-ink">
                Recommended Alternates
              </h2>
              <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
                {brief.alternates.length} routes found
              </span>
            </div>
            <AlternatesPanel
              alternates={brief.alternates}
              chosenId={chosenId}
              onSelect={(id) => setChosenId(id)}
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-base font-semibold text-ink">
                Safety Hotspots
              </h2>
              <InfoDot />
            </div>
            {hotspots.length === 0 ? (
              <p className="rounded-sm bg-paper-3 px-3 py-4 text-xs text-ink-3 ring-1 ring-rule">
                No critical hotspots on the chosen route — clean stretch for
                tonight&apos;s conditions.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {hotspots.map((h) => (
                  <HotspotRow
                    key={h.hotspot_id}
                    h={h}
                    onClick={() =>
                      setSelection({ kind: "hotspot", data: h })
                    }
                  />
                ))}
              </ul>
            )}
          </div>

          {newsArticles.length > 0 && (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-base font-semibold text-ink">
                  Media Coverage
                </h2>
                <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
                  {newsArticles.length} article{newsArticles.length !== 1 ? "s" : ""}
                </span>
              </div>
              <ul className="flex flex-col gap-2">
                {newsArticles.map((n) => (
                  <NewsRow
                    key={n.article_id}
                    article={n}
                    onClick={() =>
                      setSelection({ kind: "news", data: n })
                    }
                  />
                ))}
              </ul>
            </div>
          )}

          {brief.fatigue_plan.suggested_stops.length > 0 && (
            <div>
              <h2 className="mb-2 text-base font-semibold text-ink">
                Suggested Stops
              </h2>
              <ul className="flex flex-col divide-y divide-rule rounded-sm bg-paper-3 ring-1 ring-rule">
                {brief.fatigue_plan.suggested_stops.map((s, i) => (
                  <li key={i} className="flex items-center justify-between px-3 py-2.5">
                    <span className="text-sm text-ink">{s.label}</span>
                    <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
                      {s.km_into_trip.toFixed(0)} km
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <button
          type="button"
          className="sticky bottom-0 mt-auto border-t border-rule bg-ink py-4 text-sm font-semibold uppercase tracking-[0.14em] text-paper transition hover:bg-ink-2"
        >
          Start Guided Trip
        </button>
      </aside>

      {/* Briefing card overlay (mockup 1) */}
      {selection && (
        <BriefingCard
          subject={selection}
          onClose={() => setSelection(null)}
        />
      )}
    </main>
  );
}

function calloutToneFor(ratio: number): { label: string; bg: string } {
  // Tier the callout to the *actual* intensity so the eyebrow doesn't lie:
  //   >= 2.0x  → "HIGH RISK ZONE" (alert red)
  //   >= 1.2x  → "ELEVATED RISK"  (warn gold)
  //   < 1.2x   → "WATCH ZONE"     (ink — informational, not alarming)
  if (ratio >= 2) return { label: "High Risk Zone", bg: "bg-alert" };
  if (ratio >= 1.2) return { label: "Elevated Risk", bg: "bg-warn" };
  return { label: "Watch Zone", bg: "bg-ink" };
}

function HotspotRow({
  h,
  onClick,
}: {
  h: HotspotSummary;
  onClick: () => void;
}) {
  const tone =
    (h.intensity_ratio ?? 0) >= 2.5
      ? "alert"
      : (h.intensity_ratio ?? 0) >= 1.5
        ? "warn"
        : "muted";
  const toneStyles =
    tone === "alert"
      ? "bg-alert-2 text-alert"
      : tone === "warn"
        ? "bg-gold/15 text-gold"
        : "bg-paper text-ink-3";
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className="flex w-full items-start gap-3 rounded-sm bg-paper-3 p-3 text-left ring-1 ring-rule transition hover:ring-ink"
      >
        <span
          className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-sm ${toneStyles}`}
        >
          {tone === "alert" ? <Triangle /> : <EyeOff />}
        </span>
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-ink">{h.label}</span>
          <span className="text-xs text-ink-3">{h.coaching_line}</span>
          <span
            className={`mt-1 inline-flex w-fit items-center rounded-sm px-1.5 py-0.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] ${
              tone === "alert"
                ? "bg-alert text-paper"
                : tone === "warn"
                  ? "bg-gold text-paper"
                  : "bg-ink-3/15 text-ink-3"
            }`}
          >
            {tone === "alert"
              ? "Critical"
              : tone === "warn"
                ? "Warning"
                : "Notice"}
          </span>
        </div>
      </button>
    </li>
  );
}

function NewsRow({
  article,
  onClick,
}: {
  article: NewsArticle;
  onClick: () => void;
}) {
  const severityTone =
    article.severity === "fatal"
      ? "alert"
      : article.severity === "serious"
        ? "warn"
        : "muted";
  const badgeStyles =
    severityTone === "alert"
      ? "bg-alert text-paper"
      : severityTone === "warn"
        ? "bg-gold text-paper"
        : "bg-[#2563eb]/15 text-[#2563eb]";
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className="flex w-full items-start gap-3 rounded-sm bg-paper-3 p-3 text-left ring-1 ring-rule transition hover:ring-ink"
      >
        <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-sm bg-[#2563eb]/15 text-[#2563eb]">
          <NewsIcon />
        </span>
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-ink">
            {article.headline}
          </span>
          <span className="text-xs text-ink-3">
            {article.publisher}
            {article.publish_date ? ` · ${article.publish_date}` : ""}
          </span>
          <span
            className={`mt-1 inline-flex w-fit items-center rounded-sm px-1.5 py-0.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] ${badgeStyles}`}
          >
            {article.severity === "fatal"
              ? "Fatal"
              : article.severity === "serious"
                ? "Serious"
                : "Report"}
          </span>
        </div>
      </button>
    </li>
  );
}

function NewsIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="2" width="12" height="12" rx="1.5" />
      <path d="M5 5h6M5 8h6M5 11h3" />
    </svg>
  );
}

function InfoDot() {
  return (
    <span
      aria-hidden
      className="grid h-5 w-5 place-items-center rounded-full bg-ink text-[0.625rem] font-semibold text-paper"
    >
      i
    </span>
  );
}

function Triangle() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 0 L12 11 L0 11 Z" />
    </svg>
  );
}

function EyeOff() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M2 2l12 12" />
      <path d="M2.5 8s2-4 5.5-4 5.5 4 5.5 4-2 4-5.5 4S2.5 8 2.5 8Z" />
      <circle cx="8" cy="8" r="2" />
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
