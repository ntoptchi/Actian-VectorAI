"use client";

import type {
  HotspotSummary,
  NewsArticle,
  TripBriefResponse,
} from "~/lib/types";
import { AlternatesPanel } from "./AlternatesPanel";

type Selection =
  | { kind: "hotspot"; data: HotspotSummary }
  | { kind: "news"; data: NewsArticle };

interface Props {
  brief: TripBriefResponse;
  chosenId: string | null;
  hotspots: HotspotSummary[];
  newsArticles: NewsArticle[];
  onChangeAlternate: (routeId: string) => void;
  onSelect: (s: Selection) => void;
}

/**
 * The four "right rail" sections shared by the desktop aside and the
 * mobile draggable sheet's expanded state:
 *
 *   1. Recommended Route (+ alternates)
 *   2. Safety Hotspots list
 *   3. Media Coverage list (only when news is present)
 *   4. Suggested Stops list (only when any stops are present)
 *
 * Lives in its own file so the two surfaces can't drift. The section
 * header ("Tonight's Route") and the bottom "Open full briefing" link
 * stay with the caller — desktop keeps its big display hero, mobile
 * uses its sheet handle for the analogous affordance.
 */
export function SidebarSections({
  brief,
  chosenId,
  hotspots,
  newsArticles,
  onChangeAlternate,
  onSelect,
}: Props) {
  return (
    <>
      <div>
        <div className="mb-2 flex flex-col gap-0.5">
          <h2 className="text-base font-semibold text-ink">
            Recommended Route
          </h2>
          {brief.alternates.length > 1 && (
            <p className="text-xs text-ink-3">
              Compared against {brief.alternates.length - 1}{" "}
              {brief.alternates.length - 1 === 1 ? "alternate" : "alternates"} —
              pick any to see its briefing.
            </p>
          )}
        </div>
        <AlternatesPanel
          alternates={brief.alternates}
          chosenId={chosenId}
          onSelect={onChangeAlternate}
        />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-base font-semibold text-ink">Safety Hotspots</h2>
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
                onClick={() => onSelect({ kind: "hotspot", data: h })}
              />
            ))}
          </ul>
        )}
      </div>

      {newsArticles.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-base font-semibold text-ink">Media Coverage</h2>
            <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
              {newsArticles.length} article
              {newsArticles.length !== 1 ? "s" : ""}
            </span>
          </div>
          <ul className="flex flex-col gap-2">
            {newsArticles.map((n) => (
              <NewsRow
                key={n.article_id}
                article={n}
                onClick={() => onSelect({ kind: "news", data: n })}
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
              <li
                key={i}
                className="flex items-center justify-between px-3 py-2.5"
              >
                <span className="text-sm text-ink">{s.label}</span>
                <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
                  {s.km_into_trip.toFixed(0)} km
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
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
  // Critical hotspots tier amber, not red — a crash cluster is a
  // heads-up, not an emergency. Amber-700 ("gold-strong") keeps it
  // visually distinct from the amber-600 warning tier below.
  const toneStyles =
    tone === "alert"
      ? "bg-gold-strong/15 text-gold-strong"
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
                ? // Hex literal instead of `bg-gold-strong` because the
                  // plain full-opacity utility was silently not being
                  // emitted (see note in BriefingView's hotspotTone) —
                  // left Critical pills here unfilled.
                  "bg-[#b45309] text-paper"
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
