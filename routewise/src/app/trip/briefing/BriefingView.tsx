"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

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
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-16 px-6 py-12">
      <div>
        <Link
          href={mapHref}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-3 transition hover:text-ink"
        >
          ← Back to map
        </Link>
      </div>

      {/* Section 1 — Trip identity */}
      <section className="flex flex-col gap-6">
        <span className="eyebrow">Tonight&apos;s drive</span>
        <h1 className="display text-4xl sm:text-5xl">
          {originName ?? "Your origin"} → {destName ?? "your destination"}
        </h1>
        <p className="max-w-[52ch] text-base leading-relaxed text-ink-3">
          {brief.conditions_banner.summary}
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-sm bg-paper-3 p-5 ring-1 ring-rule sm:grid-cols-4">
          <Stat label="Distance" value={`${distanceKm} km`} />
          <Stat label="Drive time" value={durationText} />
          <Stat label="Depart" value={formatClock(depart)} sub={formatDay(depart)} />
          <Stat label="Arrive" value={formatClock(arrive)} sub={formatDay(arrive)} />
        </dl>
        <div className="flex flex-col gap-1.5 rounded-sm border-l-[3px] border-ink bg-paper-3 p-4 ring-1 ring-rule">
          <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
            Recommended route
          </span>
          <p className="text-sm leading-relaxed text-ink">
            {routeIntro(chosen, chosenMatches, brief.alternates.length)}
          </p>
        </div>
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
        <section className="flex flex-col gap-5">
          <div className="flex items-baseline justify-between gap-3">
            <span className="eyebrow eyebrow-rule">
              <span>Before you leave</span>
            </span>
            <span className="shrink-0 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-ink-3">
              {doneCount} of {checklistTotal} done
            </span>
          </div>
          <ul className="flex flex-col gap-2">
            {brief.pre_trip_checklist.map((item, i) => (
              <ChecklistItem
                key={i}
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
          <ol className="relative flex flex-col gap-5 border-l border-rule pl-6">
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
      <section className="flex flex-col gap-5 rounded-sm bg-paper-3 p-6 ring-1 ring-rule">
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
        <div className="flex flex-wrap gap-3">
          <Link
            href={mapHref}
            aria-disabled={!acknowledged}
            tabIndex={acknowledged ? undefined : -1}
            className={`inline-flex items-center gap-2 rounded-sm px-4 py-2.5 text-sm font-semibold transition ${
              acknowledged
                ? "bg-ink text-paper hover:bg-ink-2"
                : "pointer-events-none bg-paper-2 text-ink-4 ring-1 ring-rule"
            }`}
          >
            Back to route map →
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-2 py-2.5 text-sm font-medium text-ink-3 transition hover:text-ink"
          >
            Plan another trip
          </Link>
        </div>
      </section>
    </main>
  );
}

/* ------------------------------ sub-components ------------------------------ */

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-3">
        {label}
      </dt>
      <dd className="font-display text-xl font-semibold leading-tight text-ink">
        {value}
      </dd>
      {sub && <dd className="text-[0.6875rem] text-ink-3">{sub}</dd>}
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
      <span className="stat-numeral text-4xl text-ink">{value}</span>
      <span className="text-xs leading-snug text-ink-3">{label}</span>
    </div>
  );
}

function ChecklistItem({
  text,
  checked,
  onToggle,
}: {
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
        className={`flex w-full items-start gap-3 rounded-sm p-3 text-left ring-1 ring-rule transition ${
          checked
            ? "bg-paper-2 text-ink-3"
            : "bg-paper-3 text-ink hover:bg-paper-2"
        }`}
      >
        <span
          aria-hidden
          className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-sm border transition ${
            checked
              ? "border-ink bg-ink text-paper"
              : "border-rule bg-paper text-transparent"
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
        <span
          className={`flex-1 text-sm leading-snug ${
            checked ? "line-through decoration-ink-4" : ""
          }`}
        >
          {text}
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
    return (
      <li className="relative">
        <span
          aria-hidden
          className={`absolute -left-[30px] top-1.5 h-3 w-3 rounded-full ring-2 ring-paper ${tone.dotBg}`}
        />
        <div className="flex flex-col gap-2 rounded-sm bg-paper-3 p-4 ring-1 ring-rule">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-3">
                km {h.km_into_trip.toFixed(0)}
              </span>
              {eta && (
                <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-4">
                  · ~{eta}
                </span>
              )}
            </div>
            <span
              className={`shrink-0 rounded-sm px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.14em] ${tone.pillBg}`}
            >
              {tone.label}
            </span>
          </div>
          <h3 className="text-base font-semibold text-ink">{h.label}</h3>
          <p className="text-sm leading-relaxed text-ink-3">
            {h.coaching_line}
          </p>
          {(h.n_crashes > 0 || h.top_factors.length > 0) && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1 font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-4">
              {h.n_crashes > 0 && (
                <span>
                  {h.n_crashes} matched crash{h.n_crashes === 1 ? "" : "es"}
                </span>
              )}
              {h.intensity_ratio != null && (
                <span>{h.intensity_ratio.toFixed(1)}x FL avg</span>
              )}
              {h.top_factors[0] && (
                <span>Top factor · {h.top_factors[0].factor}</span>
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
          className="absolute -left-[30px] top-1.5 h-3 w-3 rounded-full bg-ink-4 ring-2 ring-paper"
        />
        <div className="flex items-start justify-between gap-3 rounded-sm bg-paper-2 p-3 ring-1 ring-rule">
          <div className="flex flex-col gap-0.5">
            <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-3">
              Rest stop · km {item.km.toFixed(0)}
              {eta && ` · ~${eta}`}
            </span>
            <span className="text-sm text-ink">{item.data.label}</span>
          </div>
          <span className="shrink-0 font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-4">
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
        className="absolute -left-[30px] top-1.5 h-3 w-3 rounded-full bg-gold ring-2 ring-paper"
      />
      <div className="flex items-start justify-between gap-3 rounded-sm bg-paper-2 p-3 ring-1 ring-rule">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-3">
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

/* --------------------------------- helpers --------------------------------- */

function hotspotTone(h: HotspotSummary): {
  label: string;
  dotBg: string;
  pillBg: string;
} {
  // Matches the tiers used in TripView's HotspotRow so the teen sees
  // consistent wording between the map list and the readthrough.
  const r = h.intensity_ratio ?? 0;
  if (r >= 2.5) {
    return {
      label: "Critical",
      dotBg: "bg-alert",
      pillBg: "bg-alert text-paper",
    };
  }
  if (r >= 1.5) {
    return {
      label: "Watch",
      dotBg: "bg-gold",
      pillBg: "bg-gold text-paper",
    };
  }
  return {
    label: "Notice",
    dotBg: "bg-ink-3",
    pillBg: "bg-ink-3/15 text-ink-3",
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
