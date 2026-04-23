"use client";

import { useEffect, useRef, useState } from "react";
import type {
  HotspotSummary,
  NewsArticle,
  RiskBand,
  RouteSegment,
} from "~/lib/types";

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "segment"; data: RouteSegment }
  | { kind: "news"; data: NewsArticle };

interface Props {
  subject: Selection;
  segments: RouteSegment[];
  onClose: () => void;
  onNavigate: (s: Selection) => void;
}

const RISK_COLOR: Record<RiskBand, string> = {
  low: "#4ade80",
  moderate: "#fbbf24",
  elevated: "#fb923c",
  high: "#ef4444",
};

/** Derive a stable key so content crossfades when the user switches items. */
function subjectKey(s: Selection): string {
  if (s.kind === "segment") return `seg-${s.data.segment_id}`;
  if (s.kind === "hotspot") return `hs-${s.data.hotspot_id}`;
  return `news-${s.data.article_id}`;
}

export function MobileBottomCard({
  subject,
  segments,
  onClose,
  onNavigate,
}: Props) {
  // Track content key changes so we can re-trigger the crossfade animation.
  const [contentKey, setContentKey] = useState(() => subjectKey(subject));
  const prevKeyRef = useRef(contentKey);

  useEffect(() => {
    const newKey = subjectKey(subject);
    if (newKey !== prevKeyRef.current) {
      prevKeyRef.current = newKey;
      setContentKey(newKey);
    }
  }, [subject]);

  return (
    <>
      {/* Backdrop — fade in */}
      <div
        className="anim-fade-in fixed inset-0 z-[1100] bg-ink/30 lg:hidden"
        onClick={onClose}
      />

      {/* Card — slide up */}
      <div className="anim-sheet-up fixed bottom-0 left-0 right-0 z-[1200] flex max-h-[65vh] flex-col rounded-t-2xl bg-paper-2 shadow-[0_-12px_40px_rgba(11,31,68,0.3)] lg:hidden">
        {/* Handle + close */}
        <div className="relative flex items-center px-4 pb-2 pt-3">
          <div className="mx-auto h-1 w-8 rounded-full bg-ink-4/40" />
          <button
            type="button"
            onPointerDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onClose();
            }}
            aria-label="Close"
            className="absolute right-3 top-2 z-10 grid h-9 w-9 place-items-center rounded-full bg-paper-3 text-ink-3 shadow-sm ring-1 ring-rule transition active:scale-90"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            >
              <path d="M1 1l10 10M11 1L1 11" />
            </svg>
          </button>
        </div>

        {/* Content — scrollable, crossfades on item change */}
        <div
          key={contentKey}
          className="anim-content-in flex-1 overflow-y-auto px-4 pb-[max(1rem,env(safe-area-inset-bottom))]"
        >
          {subject.kind === "segment" && (
            <SegmentCard
              segment={subject.data}
              segments={segments}
              onNavigate={onNavigate}
            />
          )}
          {subject.kind === "hotspot" && (
            <HotspotCard hotspot={subject.data} />
          )}
          {subject.kind === "news" && <NewsCard article={subject.data} />}
        </div>
      </div>
    </>
  );
}

/* ─────────────── Segment Card ─────────────── */

function SegmentCard({
  segment,
  segments,
  onNavigate,
}: {
  segment: RouteSegment;
  segments: RouteSegment[];
  onNavigate: (s: Selection) => void;
}) {
  const idx = segments.findIndex((s) => s.segment_id === segment.segment_id);
  const hasPrev = idx > 0;
  const hasNext = idx < segments.length - 1;
  const top = segment.top_factors[0];

  return (
    <div className="flex flex-col gap-4 pb-4">
      {/* Risk bar */}
      <RiskBar segments={segments} activeId={segment.segment_id} onNavigate={onNavigate} />

      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">
            {segment.from_km.toFixed(0)} – {segment.to_km.toFixed(0)} km
          </h3>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-ink-3">
            {segment.speed_limit_mph != null && (
              <span>{segment.speed_limit_mph} mph</span>
            )}
            {segment.aadt != null && (
              <span>· AADT {segment.aadt.toLocaleString()}</span>
            )}
          </div>
        </div>
        <span
          className="shrink-0 rounded-sm px-2 py-1 text-[0.625rem] font-bold uppercase tracking-wider"
          style={{
            backgroundColor: RISK_COLOR[segment.risk_band],
            color: segment.risk_band === "low" ? "#0b1f44" : "#fff",
          }}
        >
          {segment.risk_band}
        </span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3">
        <StatBox
          label="Matched crashes"
          value={String(segment.n_crashes)}
        />
        <StatBox
          label="vs FL average"
          value={
            segment.intensity_ratio != null
              ? `${segment.intensity_ratio.toFixed(1)}x`
              : "—"
          }
          tone={intensityTone(segment.intensity_ratio)}
        />
      </div>

      {/* Top factor */}
      {top && (
        <div className="rounded-sm border-l-[3px] border-ink bg-paper-3 p-3">
          <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-3">
            Top factor
          </span>
          <p className="mt-1 text-sm text-ink">
            {top.factor}{" "}
            <span className="text-ink-3">
              · {Math.round(top.fraction * 100)}% of matched crashes
            </span>
          </p>
        </div>
      )}

      {/* Prev / Next */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          disabled={!hasPrev}
          onClick={() =>
            hasPrev &&
            onNavigate({ kind: "segment", data: segments[idx - 1]! })
          }
          className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-paper-3 py-2.5 text-sm font-medium text-ink ring-1 ring-rule transition enabled:hover:bg-paper disabled:opacity-30"
        >
          ← Prev
        </button>
        <button
          type="button"
          disabled={!hasNext}
          onClick={() =>
            hasNext &&
            onNavigate({ kind: "segment", data: segments[idx + 1]! })
          }
          className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-paper-3 py-2.5 text-sm font-medium text-ink ring-1 ring-rule transition enabled:hover:bg-paper disabled:opacity-30"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

/* ─────────────── Hotspot Card ─────────────── */

function HotspotCard({ hotspot }: { hotspot: HotspotSummary }) {
  const top = hotspot.top_factors[0];

  return (
    <div className="flex flex-col gap-4 pb-4">
      <div>
        <h3 className="text-lg font-semibold text-ink">{hotspot.label}</h3>
        <span className="text-xs text-ink-3">
          ~{hotspot.km_into_trip.toFixed(0)} km into trip
        </span>
      </div>

      {/* Coaching */}
      <div className="rounded-sm border-l-[3px] border-ink bg-[#e7ecf4] p-3">
        <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-2">
          Coaching
        </span>
        <p className="mt-1 text-sm leading-relaxed text-ink">
          {hotspot.coaching_line}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatBox label="Matched crashes" value={String(hotspot.n_crashes)} />
        <StatBox
          label="vs FL average"
          value={
            hotspot.intensity_ratio != null
              ? `${hotspot.intensity_ratio.toFixed(1)}x`
              : "—"
          }
          tone={intensityTone(hotspot.intensity_ratio)}
        />
      </div>

      {/* Top factor */}
      {top && (
        <div className="rounded-sm bg-paper-3 p-3 ring-1 ring-rule">
          <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-3">
            Top factor
          </span>
          <p className="mt-1 text-sm text-ink">
            {top.factor}{" "}
            <span className="text-ink-3">
              · {Math.round(top.fraction * 100)}%
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

/* ─────────────── News Card ─────────────── */

function NewsCard({ article }: { article: NewsArticle }) {
  const severity =
    article.severity === "fatal"
      ? { label: "Fatal", color: "bg-alert text-paper" }
      : article.severity === "serious"
        ? { label: "Serious", color: "bg-gold text-paper" }
        : { label: "Report", color: "bg-[#2563eb]/15 text-[#2563eb]" };

  return (
    <div className="flex flex-col gap-4 pb-4">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold leading-tight text-ink">
            {article.headline}
          </h3>
          <span
            className={`shrink-0 rounded-sm px-2 py-0.5 text-[0.625rem] font-bold uppercase tracking-wider ${severity.color}`}
          >
            {severity.label}
          </span>
        </div>
        <span className="mt-1 text-xs text-ink-3">
          {article.publisher}
          {article.publish_date ? ` · ${article.publish_date}` : ""}
        </span>
      </div>

      {/* Excerpt */}
      <div className="rounded-sm border-l-[3px] border-[#2563eb] bg-[#e7ecf4] p-3">
        <p className="line-clamp-4 text-sm italic leading-relaxed text-ink">
          &ldquo;{article.excerpt}&rdquo;
        </p>
      </div>

      {/* Link to original */}
      {article.article_url && (
        <a
          href={article.article_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 rounded-sm bg-[#2563eb] px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-[#1d4ed8]"
        >
          Read original article
          <svg
            width="12"
            height="12"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 3H3v10h10v-3" />
            <path d="M9 2h5v5" />
            <path d="M14 2L7 9" />
          </svg>
        </a>
      )}
    </div>
  );
}

/* ─────────────── Risk Bar ─────────────── */

function RiskBar({
  segments,
  activeId,
  onNavigate,
}: {
  segments: RouteSegment[];
  activeId: string;
  onNavigate: (s: Selection) => void;
}) {
  if (segments.length === 0) return null;

  const totalKm = Math.max(
    1,
    segments[segments.length - 1]!.to_km - segments[0]!.from_km,
  );

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[0.625rem] font-semibold uppercase tracking-wider text-ink-3">
        Route segments
      </span>
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {segments.map((seg) => {
          const width = ((seg.to_km - seg.from_km) / totalKm) * 100;
          const isActive = seg.segment_id === activeId;
          return (
            <button
              key={seg.segment_id}
              type="button"
              onClick={() =>
                onNavigate({ kind: "segment", data: seg })
              }
              className="relative transition-opacity"
              style={{
                width: `${Math.max(width, 2)}%`,
                backgroundColor: RISK_COLOR[seg.risk_band],
                opacity: isActive ? 1 : 0.45,
              }}
              aria-label={`Segment ${seg.from_km.toFixed(0)}–${seg.to_km.toFixed(0)} km, ${seg.risk_band} risk`}
            >
              {isActive && (
                <span className="absolute inset-0 ring-2 ring-ink rounded-sm" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────── Helpers ─────────────── */

function StatBox({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "good" | "warn" | "alert" | "neutral";
}) {
  const valueColor =
    tone === "good"
      ? "text-good"
      : tone === "warn"
        ? "text-gold"
        : tone === "alert"
          ? "text-alert"
          : "text-ink";
  return (
    <div className="flex flex-col gap-1 rounded-sm bg-paper-3 p-3 ring-1 ring-rule">
      <span className={`font-display text-2xl font-semibold ${valueColor}`}>
        {value}
      </span>
      <span className="text-[0.625rem] uppercase tracking-wider text-ink-3">
        {label}
      </span>
    </div>
  );
}

function intensityTone(
  ratio: number | null | undefined,
): "good" | "warn" | "alert" | "neutral" {
  if (ratio == null) return "neutral";
  if (ratio < 1) return "good";
  if (ratio < 2) return "warn";
  return "alert";
}
