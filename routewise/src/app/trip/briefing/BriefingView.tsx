"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { humanizeFactor } from "~/lib/factors";
import type {
  AlternateSummary,
  FatigueStop,
  HotspotSummary,
  TripBriefResponse,
  WeatherSegment,
} from "~/lib/types";

interface Props {
  brief: TripBriefResponse;
  originName: string | null;
  destName: string | null;
  mapHref: string;
}

/**
 * Merged timeline of everything the driver will physically encounter,
 * ordered by km into the trip. Keeps hotspots, rest stops, and the
 * sunset crossover in a single scroll-read so the teen doesn't have to
 * cross-reference three lists mid-briefing.
 */
type TimelineItem =
  | {
      kind: "hotspot";
      km: number;
      etaIso: string | null;
      data: HotspotSummary;
    }
  | { kind: "stop"; km: number; etaIso: string; data: FatigueStop }
  | { kind: "sunset"; km: number; etaIso: string };

export function BriefingView({ brief, originName, destName, mapHref }: Props) {
  const depart = useMemo(
    () => new Date(brief.route.departure_iso),
    [brief.route.departure_iso],
  );
  const arrive = useMemo(
    () => new Date(brief.route.arrival_iso),
    [brief.route.arrival_iso],
  );
  const distanceKm = Math.round(brief.route.distance_m / 1000);
  const durationMin = Math.round(brief.route.duration_s / 60);
  const durationText = fmtDuration(durationMin);

  const chosen = useMemo<AlternateSummary | null>(
    () =>
      brief.alternates.find((a) => a.route_id === brief.chosen_route_id) ??
      null,
    [brief.alternates, brief.chosen_route_id],
  );
  const chosenMatches = chosen?.n_crashes ?? sumCrashes(brief);

  const timeline = useMemo<TimelineItem[]>(() => {
    const items: TimelineItem[] = [];
    for (const h of brief.hotspots) {
      items.push({
        kind: "hotspot",
        km: h.km_into_trip,
        etaIso: etaAtKm(h.km_into_trip, distanceKm, depart, arrive),
        data: h,
      });
    }
    for (const s of brief.fatigue_plan.suggested_stops) {
      items.push({
        kind: "stop",
        km: s.km_into_trip,
        etaIso: s.eta_iso,
        data: s,
      });
    }
    if (brief.conditions_banner.sunset_iso) {
      const sunsetKm = kmAtIso(
        brief.conditions_banner.sunset_iso,
        depart,
        arrive,
        distanceKm,
      );
      if (sunsetKm != null && sunsetKm > 2 && sunsetKm < distanceKm - 2) {
        items.push({
          kind: "sunset",
          km: sunsetKm,
          etaIso: brief.conditions_banner.sunset_iso,
        });
      }
    }
    items.sort((a, b) => a.km - b.km);
    return items;
  }, [brief, distanceKm, depart, arrive]);

  // Lightweight client-only checklist state — a teen's motivating
  // progress indicator, not persisted. Resetting on refresh is fine; it
  // encourages re-reading before a fresh drive.
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const doneCount = Object.values(checked).filter(Boolean).length;
  const checklistTotal = brief.pre_trip_checklist.length;

  const [acknowledged, setAcknowledged] = useState(false);

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 pb-10 pt-5 sm:gap-12 sm:px-6 sm:pb-14 sm:pt-6">
      <div>
        <Link
          href={mapHref}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-3 transition hover:text-ink"
        >
          ← Back to map
        </Link>
      </div>

      {/* Section 1 — Trip identity */}
      <section className="flex flex-col gap-3 sm:gap-4">
        <span className="eyebrow">Tonight&apos;s drive</span>
        <h1 className="display text-[1.75rem] leading-[1.05] sm:text-4xl md:text-5xl">
          {originName ?? "Your origin"} → {destName ?? "your destination"}
        </h1>
        <p className="max-w-[52ch] text-[0.9375rem] leading-relaxed text-ink-3 sm:text-base">
          {brief.conditions_banner.summary}
        </p>
        <SummaryStats
          items={[
            {
              label: "Distance",
              value: `${distanceKm} km`,
              icon: "distance",
            },
            {
              label: "Drive time",
              value: durationText,
              icon: "duration",
            },
            {
              label: "Depart",
              value: formatClock(depart),
              sub: formatDay(depart),
              icon: "depart",
            },
            {
              label: "Arrive",
              value: formatClock(arrive),
              sub: formatDay(arrive),
              icon: "arrive",
            },
          ]}
        />
        <RecommendedRouteCard
          chosen={chosen}
          chosenMatches={chosenMatches}
          altCount={brief.alternates.length}
          intro={routeIntro(chosen, chosenMatches, brief.alternates.length)}
        />
      </section>

      {/* Section 2 — Conditions tonight */}
      <section className="flex flex-col gap-5">
        <span className="eyebrow eyebrow-rule">
          <span>Conditions tonight</span>
        </span>
        <WeatherBreakdown
          segments={brief.conditions_banner.weather_segments}
          totalKm={distanceKm}
          depart={depart}
          arrive={arrive}
        />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {brief.conditions_banner.sunset_iso && (
            <ConditionStat
              label="Sunset"
              value={formatClock(new Date(brief.conditions_banner.sunset_iso))}
              caption={
                brief.sunset_during_trip
                  ? "during your drive"
                  : "before you arrive"
              }
            />
          )}
          <ConditionStat
            label="After-dark driving"
            value={fmtDuration(brief.conditions_banner.dark_drive_minutes)}
            caption={
              brief.conditions_banner.dark_drive_minutes > 0
                ? "headlights-on stretch"
                : "daylight the whole way"
            }
          />
          {surfaceSummary(brief.conditions_banner.weather_segments) && (
            <ConditionStat
              label="Road surface"
              value={surfaceSummary(brief.conditions_banner.weather_segments)!}
              caption="across the drive"
            />
          )}
        </div>
      </section>

      {/* Section 3 — Pre-trip checklist */}
      {checklistTotal > 0 && (
        <section className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between gap-3">
            <span className="eyebrow eyebrow-rule">
              <span>Before you leave</span>
            </span>
            <span className="shrink-0 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
              {doneCount} / {checklistTotal}
            </span>
          </div>
          {/* Progress rail — a briefing earns a progress bar, not a
              todo list. Shows commitment-to-completion at a glance. */}
          <div
            className="h-[3px] w-full overflow-hidden rounded-full bg-paper-2"
            aria-hidden
          >
            <div
              className="h-full bg-ink transition-[width] duration-300 ease-out"
              style={{
                width: `${
                  checklistTotal === 0
                    ? 0
                    : Math.round((doneCount / checklistTotal) * 100)
                }%`,
              }}
            />
          </div>
          <ul className="flex flex-col divide-y divide-rule overflow-hidden rounded-sm bg-paper-3 ring-1 ring-rule">
            {brief.pre_trip_checklist.map((item, i) => (
              <ChecklistItem
                key={i}
                index={i}
                text={item}
                checked={!!checked[i]}
                onToggle={() =>
                  setChecked((prev) => ({ ...prev, [i]: !prev[i] }))
                }
              />
            ))}
          </ul>
        </section>
      )}

      {/* Section 4 — Timeline of the drive */}
      <section className="flex flex-col gap-5">
        <span className="eyebrow eyebrow-rule">
          <span>What you&apos;ll see along the way</span>
        </span>
        <p className="max-w-[60ch] text-sm text-ink-3">
          Every hotspot and rest stop, in the order you&apos;ll hit them.
          Read the coaching line before you go — you won&apos;t have time
          to scroll it at 70 mph.
        </p>
        {timeline.length === 0 ? (
          <div className="rounded-sm bg-paper-3 px-4 py-6 text-sm text-ink-3 ring-1 ring-rule">
            Clean stretch — no matched hotspots or fatigue-flagged rest
            points on this route for tonight&apos;s conditions. Drive the
            speed limit and keep your eyes up anyway.
          </div>
        ) : (
          // Receded rail: deliberately faint (ink-4/30) so the cards
          // are the headline act. The rail is *connective tissue*,
          // not a competing element. Critical hotspot dots retain a
          // heavier size + color so active warnings still punch
          // through the quieter structure around them.
          <ol className="relative flex flex-col gap-5 pl-7 before:absolute before:bottom-1 before:left-[3px] before:top-1 before:w-[2px] before:rounded-full before:bg-ink-4/30">
            {timeline.map((item, i) => (
              <TimelineNode key={`${item.kind}-${i}`} item={item} />
            ))}
          </ol>
        )}
      </section>

      {/* Section 5 — Key numbers */}
      <section className="flex flex-col gap-5">
        <span className="eyebrow eyebrow-rule">
          <span>The numbers behind the brief</span>
        </span>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <KeyNumber
            value={String(chosenMatches)}
            label={
              chosenMatches === 0
                ? "Crashes matching tonight’s conditions on this route"
                : `Crash${chosenMatches === 1 ? "" : "es"} matching tonight’s conditions`
            }
          />
          <KeyNumber
            value={String(brief.hotspots.length)}
            label={
              brief.hotspots.length === 1
                ? "Hotspot to watch"
                : "Hotspots to watch"
            }
          />
          <KeyNumber
            value={fmtDuration(brief.conditions_banner.dark_drive_minutes)}
            label="After-dark driving"
          />
          <KeyNumber
            value={String(brief.fatigue_plan.suggested_stops.length)}
            label={
              brief.fatigue_plan.suggested_stops.length === 1
                ? "Suggested rest stop"
                : "Suggested rest stops"
            }
          />
        </div>
      </section>

      {/* Section 6 — Ready to drive */}
      <section className="flex flex-col gap-5 rounded-sm bg-paper-3 p-5 ring-1 ring-rule sm:p-6">
        <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
          Ready to drive
        </span>
        <h2 className="text-2xl font-semibold text-ink">
          You&apos;ve got tonight&apos;s picture.
        </h2>
        <p className="max-w-[60ch] text-sm leading-relaxed text-ink-3">
          RouteWise surfaces patterns from past crashes under conditions
          like yours tonight. It&apos;s a briefing, not autopilot — keep
          your eyes up, phone down, and leave extra space on the stretches
          flagged above.
        </p>
        <label className="flex cursor-pointer items-start gap-3 text-sm text-ink">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-rule accent-ink"
          />
          <span>I&apos;ve read the briefing and I&apos;m good to drive.</span>
        </label>
        {/* CTA stack: one primary action, one quieter secondary link.
            Primary is the logo's charcoal ink at full saturation when
            enabled — same chip-of-paint as the masthead mark, so it
            reads as *the* action, not a styled link. When locked it
            drops to a muted paper-2 fill with a helper line calling
            out exactly what's blocking it. Secondary is pure text. */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-5">
          <Link
            href={mapHref}
            aria-disabled={!acknowledged}
            tabIndex={acknowledged ? undefined : -1}
            className={`inline-flex items-center justify-center gap-2 rounded-sm px-6 py-3 text-sm font-semibold tracking-tight transition-colors duration-200 ${
              acknowledged
                ? "bg-ink text-paper hover:bg-ink-2"
                : "pointer-events-none bg-paper-2 text-ink-4 ring-1 ring-rule"
            }`}
          >
            Back to the route
            <span aria-hidden>→</span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm font-medium text-ink-3 underline-offset-4 transition hover:text-ink hover:underline"
          >
            Plan another trip
          </Link>
        </div>
        {!acknowledged && (
          <span className="text-[0.6875rem] text-ink-3">
            Check the box above to unlock.
          </span>
        )}
      </section>
    </main>
  );
}

/* ------------------------------ sub-components ------------------------------ */

type SummaryIcon = "distance" | "duration" | "depart" | "arrive";

/**
 * Hero metrics row. Rendered as a single unified card with interior
 * divider lines rather than four boxed tiles — the stats belong to
 * *this* trip, so they should read as one object, not a quartet of
 * disconnected chips.
 *
 * The card sits on a very faint slate-tinted fill (paper-2) rather
 * than the page's off-white, so it anchors visually against the
 * surrounding copy without needing shadows or heavy rings. Each cell
 * gets a small stroke icon next to its label — utilitarian, not
 * decorative, at the same weight as the mono-caps label itself.
 *
 * On mobile we stack 2x2 with both axes dividered; on sm+ we flatten
 * to a single row with only vertical dividers between cells.
 */
function SummaryStats({
  items,
}: {
  items: {
    label: string;
    value: string;
    sub?: string;
    icon: SummaryIcon;
  }[];
}) {
  return (
    <dl className="grid grid-cols-2 overflow-hidden rounded-sm bg-paper-2 ring-1 ring-rule sm:grid-cols-4">
      {items.map((s, i) => {
        const cls = [
          "flex flex-col gap-1 px-4 py-4 sm:px-5",
          i % 2 === 1 && "border-l border-rule",
          i >= 2 && "border-t border-rule sm:border-t-0",
          i > 0 && "sm:border-l sm:border-rule",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <div key={s.label} className={cls}>
            <dt className="flex items-center gap-1.5 font-mono text-[0.625rem] uppercase tracking-[0.08em] text-ink-3">
              <StatIcon name={s.icon} />
              {s.label}
            </dt>
            <dd className="font-display text-2xl font-semibold leading-tight tracking-tight text-ink">
              {s.value}
            </dd>
            {s.sub && (
              <dd className="text-[0.6875rem] text-ink-3">{s.sub}</dd>
            )}
          </div>
        );
      })}
    </dl>
  );
}

function StatIcon({ name }: { name: SummaryIcon }) {
  const common = {
    width: 12,
    height: 12,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    className: "shrink-0 text-ink-3",
  };
  switch (name) {
    case "distance":
      // Segment line w/ ruler ticks — "how far."
      return (
        <svg {...common}>
          <path d="M2 8h12" />
          <path d="M4 6v4M8 5.5v5M12 6v4" />
        </svg>
      );
    case "duration":
      // Clock face — "how long."
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="5.5" />
          <path d="M8 5v3l2 1.5" />
        </svg>
      );
    case "depart":
      // Arrow leaving a dot — "from here."
      return (
        <svg {...common}>
          <circle cx="3.5" cy="8" r="1" fill="currentColor" stroke="none" />
          <path d="M6 8h7" />
          <path d="M10.5 5.5 13 8l-2.5 2.5" />
        </svg>
      );
    case "arrive":
      // Arrow into a dot — "to here."
      return (
        <svg {...common}>
          <path d="M3 8h7" />
          <path d="M7.5 5.5 10 8l-2.5 2.5" />
          <circle cx="12.5" cy="8" r="1" fill="currentColor" stroke="none" />
        </svg>
      );
  }
}

/**
 * Recommended-route card. Three jobs:
 *   1. Say *unambiguously* which route was picked (checkmark badge +
 *      "chosen" eyebrow). A thicker accent bar earns the authority.
 *   2. Explain in one line *why* it was picked ({@link routeIntro}).
 *   3. Back that up with compact metrics — matched crashes, how many
 *      alternates were considered, and the minutes-cost vs the fastest
 *      option (only shown if non-zero; zero-cost comparisons read as
 *      filler).
 */
function RecommendedRouteCard({
  chosen,
  chosenMatches,
  altCount,
  intro,
}: {
  chosen: AlternateSummary | null;
  chosenMatches: number;
  altCount: number;
  intro: string;
}) {
  const minutesCost = chosen?.minutes_delta_vs_fastest ?? 0;
  const minutesCostLabel =
    minutesCost > 0 ? `+${Math.round(minutesCost)} min vs fastest` : null;
  return (
    <div className="flex items-start gap-4 rounded-sm border-l-4 border-ink bg-paper-3 p-4 ring-1 ring-ink/15 sm:p-5">
      <span
        aria-hidden
        className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-ink text-paper"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path
            d="M2 6.5 4.7 9 10 3"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <div className="flex flex-1 flex-col gap-2">
        <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.08em] text-ink">
          Recommended route
        </span>
        <p className="text-sm leading-relaxed text-ink">{intro}</p>
        <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
          <span>
            {chosenMatches} matched crash{chosenMatches === 1 ? "" : "es"}
          </span>
          <span>
            {altCount} {altCount === 1 ? "route" : "routes"} compared
          </span>
          {minutesCostLabel && <span>{minutesCostLabel}</span>}
        </div>
      </div>
    </div>
  );
}

function ConditionStat({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-sm bg-paper-3 p-4 ring-1 ring-rule">
      <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-3">
        {label}
      </span>
      <span className="font-display text-xl font-semibold text-ink">
        {value}
      </span>
      <span className="text-xs text-ink-3">{caption}</span>
    </div>
  );
}

function KeyNumber({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col gap-2 rounded-sm bg-paper-3 p-4 ring-1 ring-rule">
      <span className="stat-numeral text-3xl text-ink sm:text-4xl">{value}</span>
      <span className="text-xs leading-snug text-ink-3">{label}</span>
    </div>
  );
}

/**
 * Editorial briefing-style checklist row. We intentionally move away
 * from the default "boxed todo" feel by:
 *   - Numbering each item (01, 02…) so the set reads as a sequence,
 *     not a flat list.
 *   - Housing all rows inside a single divided card (parent container
 *     in the caller sets the ring/divide), so individual rings don't
 *     chop the section into loose chips.
 *   - Treating the check as the right-edge affordance (briefing
 *     sign-off), not the primary visual anchor on the left.
 */
function ChecklistItem({
  index,
  text,
  checked,
  onToggle,
}: {
  index: number;
  text: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onToggle}
        aria-pressed={checked}
        className={`group flex w-full items-center gap-4 px-4 py-3 text-left transition ${
          checked ? "bg-paper-2/60" : "bg-paper-3 hover:bg-paper-2/50"
        }`}
      >
        <span
          aria-hidden
          className={`w-7 shrink-0 font-mono text-[0.6875rem] font-semibold tracking-[0.1em] tabular-nums transition ${
            checked ? "text-ink-4" : "text-ink-3"
          }`}
        >
          {String(index + 1).padStart(2, "0")}
        </span>
        <span
          className={`flex-1 text-sm leading-snug transition ${
            checked
              ? "text-ink-3 line-through decoration-ink-4/60"
              : "text-ink"
          }`}
        >
          {text}
        </span>
        <span
          aria-hidden
          className={`grid h-5 w-5 shrink-0 place-items-center rounded-sm border transition ${
            checked
              ? "border-ink bg-ink text-paper"
              : "border-rule bg-paper text-transparent group-hover:border-ink-4"
          }`}
        >
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
            <path
              d="M2 6.5 4.7 9 10 3"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>
    </li>
  );
}

/**
 * Plain-English km-by-km breakdown of the conditions the driver will
 * actually encounter. This is the primary way the driver re-reads
 * tonight's weather before putting the phone in the glovebox.
 *
 * Adjacent segments with the same weather + surface are merged into
 * one row — the backend sometimes splits a 300 km "light rain" window
 * into 20-km slices (useful for the map's weather coloring, noisy as
 * a list), so we collapse contiguous identical runs.
 *
 * Each row also carries an approximate clock-time ("~7:48 PM") so the
 * driver can match the km range to where they'll physically be in the
 * evening, which matters when one of the segments is the sunset one.
 */
function WeatherBreakdown({
  segments,
  totalKm,
  depart,
  arrive,
}: {
  segments: WeatherSegment[];
  totalKm: number;
  depart: Date;
  arrive: Date;
}) {
  const rows = mergeWeatherSegments(segments);
  if (rows.length === 0) {
    return (
      <div className="rounded-sm bg-paper-3 px-4 py-4 text-sm text-ink-3 ring-1 ring-rule">
        No weather breakdown available for this route. Drive with normal
        caution and check a live forecast before you leave.
      </div>
    );
  }

  return (
    <ol className="flex flex-col divide-y divide-rule overflow-hidden rounded-sm bg-paper-3 ring-1 ring-rule">
      {rows.map((r, i) => {
        const fromEtaIso = etaAtKm(r.from_km, totalKm, depart, arrive);
        const fromEta = fromEtaIso ? formatClock(new Date(fromEtaIso)) : null;
        return (
          <li
            key={i}
            className="grid grid-cols-[auto_auto_1fr_auto] items-center gap-x-4 gap-y-0.5 px-4 py-3"
          >
            <span
              aria-hidden
              className={`h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-rule ${surfaceStyle(r.surface)}`}
            />
            <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
              {formatKmRange(r.from_km, r.to_km)}
            </span>
            <span className="text-sm leading-snug text-ink">
              {prettyWeather(r.weather)}
              {r.surface !== "unknown" && r.surface !== "dry" && (
                <span className="text-ink-3"> · {surfaceLabel(r.surface)} roads</span>
              )}
            </span>
            {fromEta && (
              <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-4">
                ~{fromEta}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function mergeWeatherSegments(segments: WeatherSegment[]): WeatherSegment[] {
  const out: WeatherSegment[] = [];
  for (const s of segments) {
    const last = out[out.length - 1];
    if (
      last &&
      last.weather.toLowerCase() === s.weather.toLowerCase() &&
      last.surface === s.surface &&
      // Only merge truly contiguous slices — if the backend leaves a
      // gap, preserve it so the list doesn't silently cover over
      // unreported territory.
      Math.abs(last.to_km - s.from_km) < 1
    ) {
      out[out.length - 1] = { ...last, to_km: s.to_km };
    } else {
      out.push({ ...s });
    }
  }
  return out;
}

function prettyWeather(raw: string): string {
  const t = raw.trim();
  if (!t) return "Conditions unknown";
  // Capitalize the first letter of each word so "light rain" reads
  // like prose, not a database column. Everything after that stays
  // as written by the backend so we don't reinvent meteorology.
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function formatKmRange(from: number, to: number): string {
  const f = Math.round(from);
  const t = Math.round(to);
  if (f === 0) return `0 – ${t} km`;
  return `${f} – ${t} km`;
}

function TimelineNode({ item }: { item: TimelineItem }) {
  const eta = item.etaIso ? formatClock(new Date(item.etaIso)) : null;

  if (item.kind === "hotspot") {
    const h = item.data;
    const tone = hotspotTone(h);
    // Only "active warning" tiers (Critical / Watch) get the heavier
    // dot treatment; the quieter Notice tier uses the smaller
    // recessed dot so it doesn't shout from the rail.
    const activeWarning = tone.label !== "Notice";
    return (
      <li className="relative">
        <span
          aria-hidden
          className={
            activeWarning
              ? `absolute -left-[31px] top-1.5 h-3.5 w-3.5 rounded-full ring-[3px] ring-paper ${tone.dotBg}`
              : `absolute -left-[30px] top-2 h-3 w-3 rounded-full ring-2 ring-paper ${tone.dotBg}`
          }
        />
        <div
          className={`flex flex-col gap-2 rounded-sm p-4 ring-1 ${tone.cardBg} ${tone.cardRing} ${tone.accentBorder}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
                km {h.km_into_trip.toFixed(0)}
              </span>
              {eta && (
                <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
                  · ~{eta}
                </span>
              )}
            </div>
            <span
              className={`shrink-0 rounded-sm px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.08em] ${tone.pillBg}`}
            >
              {tone.label}
            </span>
          </div>
          <h3 className="text-base font-semibold text-ink">{h.label}</h3>
          <p className="text-sm leading-relaxed text-ink-3">
            {h.coaching_line}
          </p>
          {(h.n_crashes > 0 || h.top_factors.length > 0) && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
              {h.n_crashes > 0 && (
                <span>
                  {h.n_crashes} matched crash{h.n_crashes === 1 ? "" : "es"}
                </span>
              )}
              {h.intensity_ratio != null && (
                <span>{h.intensity_ratio.toFixed(1)}x FL avg</span>
              )}
              {h.top_factors[0] && (
                <span>Top factor · {humanizeFactor(h.top_factors[0].factor)}</span>
              )}
            </div>
          )}
        </div>
      </li>
    );
  }

  if (item.kind === "stop") {
    return (
      <li className="relative">
        <span
          aria-hidden
          className="absolute -left-[30px] top-2 h-3 w-3 rounded-full bg-ink-4 ring-2 ring-paper"
        />
        {/* Rest stops are *calm* — cool neutral tint, smaller dot.
            The left-border in ink-4 ties the card back to its dot
            without turning up the visual volume. */}
        <div className="flex items-start justify-between gap-3 rounded-sm border-l-2 border-ink-4/50 bg-paper-2 p-3 ring-1 ring-rule">
          <div className="flex items-center gap-2.5">
            <RestIcon />
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
                Rest stop · km {item.km.toFixed(0)}
                {eta && ` · ~${eta}`}
              </span>
              <span className="text-sm text-ink">{item.data.label}</span>
            </div>
          </div>
          <span className="shrink-0 font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
            Stretch &amp; refuel
          </span>
        </div>
      </li>
    );
  }

  return (
    <li className="relative">
      <span
        aria-hidden
        className="absolute -left-[30px] top-2 h-3 w-3 rounded-full bg-gold ring-2 ring-paper"
      />
      {/* Sunset is an *environmental change*, not an alert. A small
          sun-dipping glyph does the cognitive lifting — the reader
          doesn't have to parse the label to know "something about
          the light is changing." Faint gold tint keeps it in the
          same family as the gold dot on the rail. */}
      <div className="flex items-start gap-2.5 rounded-sm border-l-2 border-gold bg-gold/[0.06] p-3 ring-1 ring-rule">
        <SunsetIcon />
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[0.625rem] uppercase tracking-[0.06em] text-ink-3">
            Sunset · ~km {item.km.toFixed(0)} · {eta}
          </span>
          <span className="text-sm text-ink">
            Headlights on from here. Drop your speed 5 mph and double your
            following distance — your eyes need a minute to adjust.
          </span>
        </div>
      </div>
    </li>
  );
}

function RestIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="mt-0.5 shrink-0 text-ink-3"
    >
      <path d="M2 11h12" />
      <path d="M3 11V7.5a1.5 1.5 0 0 1 1.5-1.5h5A2.5 2.5 0 0 1 12 8.5V11" />
      <path d="M12 11V8.5h.5A1.5 1.5 0 0 1 14 10v1" />
    </svg>
  );
}

function SunsetIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="mt-0.5 shrink-0 text-gold-strong"
    >
      <path d="M3 11h10" />
      <path d="M5 11a3 3 0 0 1 6 0" />
      <path d="M8 3v2" />
      <path d="M3.5 5 4.6 6.1" />
      <path d="M12.5 5 11.4 6.1" />
      <path d="M1.5 11h.5M14 11h.5" />
      <path d="M8 13v1" />
    </svg>
  );
}

/* --------------------------------- helpers --------------------------------- */

function hotspotTone(h: HotspotSummary): {
  label: string;
  dotBg: string;
  pillBg: string;
  cardBg: string;
  cardRing: string;
  accentBorder: string;
} {
  // Matches the tiers used in TripView's HotspotRow so the teen sees
  // consistent wording between the map list and the readthrough.
  // Critical intentionally uses amber-700 (gold-strong), not red —
  // a crash cluster needs attention, not the hard-stop pill that red
  // reads as in road signage.
  //
  // Card-level tinting: Critical and Watch get a faint warning wash
  // (at ~4% alpha of their tier color) plus a 4px accent border on
  // the left. Notice stays neutral so it doesn't cry wolf.
  const r = h.intensity_ratio ?? 0;
  if (r >= 2.5) {
    return {
      label: "Critical",
      dotBg: "bg-gold-strong",
      pillBg: "bg-gold-strong text-paper",
      cardBg: "bg-gold-strong/[0.05]",
      cardRing: "ring-gold-strong/25",
      accentBorder: "border-l-4 border-gold-strong",
    };
  }
  if (r >= 1.5) {
    return {
      label: "Watch",
      dotBg: "bg-gold",
      pillBg: "bg-gold text-paper",
      cardBg: "bg-gold/[0.06]",
      cardRing: "ring-gold/30",
      accentBorder: "border-l-4 border-gold",
    };
  }
  return {
    label: "Notice",
    dotBg: "bg-ink-3",
    pillBg: "bg-ink-3/15 text-ink-3",
    cardBg: "bg-paper-3",
    cardRing: "ring-rule",
    accentBorder: "",
  };
}

/**
 * Muted slate-blue for wet, cool near-white for snowy/icy, neutral for
 * dry. Tonal, not alarming — a weather strip shouldn't read like a
 * crash-risk bar (we already have one of those).
 */
function surfaceStyle(surface: WeatherSegment["surface"]): string {
  switch (surface) {
    case "wet":
      return "bg-[#6b8fb8]";
    case "icy":
      return "bg-[#9ec8e6]";
    case "snowy":
      return "bg-[#d8e2ee]";
    case "unknown":
      return "bg-paper-2";
    case "dry":
    default:
      return "bg-[#cbd5e1]";
  }
}

function surfaceLabel(surface: WeatherSegment["surface"]): string {
  return surface.charAt(0).toUpperCase() + surface.slice(1);
}

function surfaceSummary(segs: WeatherSegment[]): string | null {
  const set = new Set<string>();
  for (const s of segs) {
    if (s.surface === "unknown") continue;
    set.add(surfaceLabel(s.surface));
  }
  if (set.size === 0) return null;
  return [...set].join(" · ");
}

function sumCrashes(brief: TripBriefResponse): number {
  return brief.segments.reduce((acc, s) => acc + s.n_crashes, 0);
}

function routeIntro(
  chosen: AlternateSummary | null,
  matches: number,
  altCount: number,
): string {
  const other = Math.max(0, altCount - 1);
  const comparison =
    other === 0
      ? ""
      : ` Lower than the ${other === 1 ? "other alternate" : `${other} alternates`} we considered.`;
  if (matches === 0) {
    return `Chosen for the fewest crash-matched segments tonight — zero hits for these conditions on this path.${comparison}`;
  }
  return `Chosen for the fewest crash-matched segments tonight — ${matches} hit${matches === 1 ? "" : "s"} across the full drive.${comparison}`;
}

function formatClock(d: Date): string {
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDay(d: Date): string {
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) return "today";
  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  const isTomorrow =
    d.getFullYear() === tomorrow.getFullYear() &&
    d.getMonth() === tomorrow.getMonth() &&
    d.getDate() === tomorrow.getDate();
  if (isTomorrow) return "tomorrow";
  return d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function fmtDuration(min: number): string {
  if (min <= 0) return "None";
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/**
 * Interpolate arrival time at a given km mark along the route.
 * Good enough for "approximate ETA" labels — we're not guiding, we're
 * just letting the driver know roughly when they'll hit a hotspot.
 */
function etaAtKm(
  km: number,
  totalKm: number,
  depart: Date,
  arrive: Date,
): string | null {
  if (totalKm <= 0) return null;
  const frac = Math.max(0, Math.min(1, km / totalKm));
  const ms = depart.getTime() + frac * (arrive.getTime() - depart.getTime());
  return new Date(ms).toISOString();
}

function kmAtIso(
  iso: string,
  depart: Date,
  arrive: Date,
  totalKm: number,
): number | null {
  const when = new Date(iso).getTime();
  const start = depart.getTime();
  const end = arrive.getTime();
  if (!Number.isFinite(when) || end <= start) return null;
  const frac = (when - start) / (end - start);
  if (frac < 0 || frac > 1) return null;
  return frac * totalKm;
}
