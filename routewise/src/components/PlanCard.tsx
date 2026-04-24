"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ScrollArea } from "~/components/ui/scroll-area";
import { CITIES, cityLabel, nearestCity, searchCities, type City } from "~/lib/cities";
import { cn } from "~/lib/utils";

/**
 * Landing-page trip planner.
 *
 * v1 of this card hard-coded Miami → Tampa coordinates in hidden inputs and
 * shipped two free-text fields next to them that nobody read — every
 * submission, regardless of typed text, sent the user to the same Miami →
 * Tampa briefing. This rewrite couples the visible picker (a typeahead
 * over the curated FL cities list) to the lat/lon that actually ships.
 */
export function PlanCard() {
  const router = useRouter();

  const [origin, setOrigin] = useState<City | null>(null);
  const [destination, setDestination] = useState<City | null>(null);
  const [depart, setDepart] = useState(""); // YYYY-MM-DDTHH:MM (local) from datetime-local
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);
  const [loading, setLoading] = useState(false);

  // Live wall-clock tick so the footer clock stays fresh without the user
  // refreshing. 30s resolution is plenty for a minute-grained display,
  // and the hook returns null pre-mount so Next.js SSR can't disagree
  // with the client's first paint.
  const now = useNowTick(30_000);

  // Seed Depart with the next quarter-hour on mount. Done in an effect
  // (not in useState's initializer) so SSR and client render match.
  useEffect(() => {
    if (depart) return;
    setDepart(formatDateTimeLocal(nearestQuarterHour(new Date())));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Parse whatever's in the datetime-local input into a Date for the
  // readout. Invalid / empty input → null.
  const departDate = useMemo(() => parseDateTimeLocal(depart), [depart]);

  // Great-circle distance + crude highway ETA. Only meaningful once both
  // cities are selected.
  const preview = useMemo(() => {
    if (!origin || !destination || origin.id === destination.id) return null;
    const miles = haversineMiles(origin, destination);
    const driveMin = driveMinutesFor(miles);
    const arrival =
      departDate != null
        ? new Date(departDate.getTime() + driveMin * 60_000)
        : null;
    const sunsetLocalMin = approxFLSunsetMinutes(arrival ?? new Date());
    const arrivalLocalMin = arrival
      ? arrival.getHours() * 60 + arrival.getMinutes()
      : null;
    const afterSunsetMin =
      arrivalLocalMin != null
        ? Math.max(0, arrivalLocalMin - sunsetLocalMin)
        : 0;
    return { miles, driveMin, arrival, afterSunsetMin };
  }, [origin, destination, departDate]);

  const ready = preview != null;

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (!origin) {
      setError("Pick a starting city — type a name or use Current Location.");
      return;
    }
    if (!destination) {
      setError("Pick a destination city from the list.");
      return;
    }
    if (origin.id === destination.id) {
      setError("Origin and destination can't be the same city.");
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({
      olat: String(origin.lat),
      olon: String(origin.lon),
      dlat: String(destination.lat),
      dlon: String(destination.lon),
    });
    if (depart) params.set("depart", depart);
    router.push(`/trip?${params.toString()}`);
  };

  const useCurrentLocation = () => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setError("Geolocation isn't available in this browser.");
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const match = nearestCity(lat, lon);
        const name = match?.name ?? "Current Location";
        const here: City = {
          id: `here-${lat.toFixed(4)}-${lon.toFixed(4)}`,
          name,
          state: "FL",
          lat,
          lon,
        };
        setOrigin(here);
        setLocating(false);
      },
      (err) => {
        setError(`Couldn't read your location (${err.message}).`);
        setLocating(false);
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    );
  };

  // Swap origin/destination. The tiniest feature that makes the form feel
  // like a real planner — any commuter will click this instead of
  // re-typing.
  const swap = () => {
    if (!origin && !destination) return;
    setOrigin(destination);
    setDestination(origin);
    setError(null);
  };

  const applyQuickDepart = (kind: QuickDepartKind) => {
    setDepart(formatDateTimeLocal(computeQuickDepart(kind, new Date())));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="relative self-start rounded-2xl bg-paper-3 p-4 shadow-[0_20px_40px_-20px_rgba(15,23,42,0.18)] ring-1 ring-rule sm:p-6"
    >
      <h2 className="text-base font-semibold text-ink">Where are you headed?</h2>
      <p className="mt-1 text-sm text-ink-3">
        Takes about 30 seconds. We&apos;ll flag the spots worth watching
        for.
      </p>

      <div className="mt-5 flex flex-col gap-4">
        <CityCombobox
          label="From"
          name="origin"
          placeholder="e.g. Miami"
          value={origin}
          onChange={setOrigin}
          trailing={
            <button
              type="button"
              onClick={useCurrentLocation}
              disabled={locating}
              title="Use my current location"
              className="text-ink-3 transition hover:text-ink disabled:opacity-50"
            >
              {locating ? <Spinner /> : <Crosshair />}
            </button>
          }
        />

        <div className="-my-1 flex items-center justify-end">
          <button
            type="button"
            onClick={swap}
            disabled={!origin && !destination}
            title="Swap origin and destination"
            className="inline-flex items-center gap-1.5 rounded-full border border-rule px-2.5 py-1 text-xs font-medium text-ink-3 transition hover:border-ink hover:text-ink disabled:opacity-40"
          >
            <SwapIcon />
            Swap
          </button>
        </div>

        <CityCombobox
          label="To"
          name="destination"
          placeholder="Where to?"
          value={destination}
          onChange={setDestination}
          trailing={<PinIcon />}
        />

        <div className="flex flex-col gap-2">
          <Field label="When are you leaving?" name="depart">
            <input
              name="depart"
              type="datetime-local"
              value={depart}
              onChange={(e) => setDepart(e.target.value)}
              className="w-full bg-transparent text-base text-ink placeholder:text-ink-4 focus:outline-none"
            />
          </Field>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_DEPART.map((q) => (
              <button
                key={q.kind}
                type="button"
                onClick={() => applyQuickDepart(q.kind)}
                className="rounded-full border border-rule bg-paper-2 px-2.5 py-1 text-xs font-medium text-ink-3 transition hover:border-ink hover:text-ink"
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>

        {preview && (
          <TripReadout
            origin={origin!}
            destination={destination!}
            miles={preview.miles}
            driveMin={preview.driveMin}
            arrival={preview.arrival}
            afterSunsetMin={preview.afterSunsetMin}
          />
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg border-l-2 border-alert bg-alert-2/60 px-3 py-2 text-xs text-alert"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-1 inline-flex min-h-[48px] cursor-pointer items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-semibold text-paper-3 transition hover:bg-ink-2 disabled:cursor-wait disabled:opacity-80"
        >
          {loading ? (
            <div className="route-loader" />
          ) : (
            <>
              {ready && preview
                ? `See my briefing · ~${Math.round(preview.miles)} mi · ~${formatDuration(preview.driveMin)}`
                : "See my briefing"}
              {ready && (
                <kbd className="ml-1 rounded-md border border-paper-3/30 px-1.5 py-0.5 font-mono text-[0.625rem] text-paper-3/70">
                  ⏎
                </kbd>
              )}
            </>
          )}
        </button>
        <div className="flex items-center justify-between text-xs text-ink-4">
          <span>Florida routes only · {CITIES.length} cities</span>
          {now && (
            <span className="font-mono tabular-nums">{formatClock(now)}</span>
          )}
        </div>
      </div>
    </form>
  );
}

/* ----------------------------- Readout ------------------------------- */

/**
 * Compact "here's what you're actually planning" strip, rendered as soon
 * as both cities are picked. The numbers are intentionally labelled as
 * estimates — they come from great-circle distance and a flat 55-mph
 * highway average, not from the backend router. They're for
 * at-a-glance realism on the landing form, not for anything load-bearing.
 */
function TripReadout({
  origin,
  destination,
  miles,
  driveMin,
  arrival,
  afterSunsetMin,
}: {
  origin: City;
  destination: City;
  miles: number;
  driveMin: number;
  arrival: Date | null;
  afterSunsetMin: number;
}) {
  const nightDrive = afterSunsetMin >= 15;
  const longHaul = driveMin >= 3 * 60;

  return (
    <div className="rounded-xl border border-rule bg-paper-2 px-4 py-3 text-sm leading-relaxed text-ink-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink">
        <span className="font-medium">
          {origin.name} → {destination.name}
        </span>
        <span className="text-ink-4">·</span>
        <span className="tabular-nums">~{Math.round(miles)} mi</span>
        <span className="text-ink-4">·</span>
        <span className="tabular-nums">~{formatDuration(driveMin)}</span>
        {arrival && (
          <>
            <span className="text-ink-4">·</span>
            <span className="tabular-nums">arrive {formatHHMM(arrival)}</span>
          </>
        )}
      </div>
      {(nightDrive || longHaul) && (
        <ul className="mt-2 flex flex-col gap-1 text-xs text-ink-3">
          {nightDrive && (
            <li>
              <Dot /> About {formatDuration(afterSunsetMin)} of this is after
              sunset — plan on headlights and lower speeds.
            </li>
          )}
          {longHaul && (
            <li>
              <Dot /> Long drive — plan a rest stop around the halfway point.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function Dot() {
  return (
    <span
      aria-hidden
      className="mr-1.5 inline-block h-1 w-1 -translate-y-[2px] rounded-full bg-ink-4"
    />
  );
}

/* --------------------------- City Combobox --------------------------- */

/**
 * Typeahead picker. Suggestion popover is shown only while the user is
 * actively typing; selecting an item or blurring closes it.
 *
 * The popover renders inside a shadcn/ui ScrollArea so a long match list
 * stays inside a fixed-height surface with proper scrollbar styling.
 */
function CityCombobox({
  label,
  name,
  placeholder,
  value,
  onChange,
  trailing,
}: {
  label: string;
  name: string;
  placeholder: string;
  value: City | null;
  onChange: (city: City | null) => void;
  trailing: React.ReactNode;
}) {
  const listboxId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Local text mirrors either the typed query or the selected city's label.
  // We keep them as one piece of state so a parent-driven `value` change
  // (e.g. "Use Current Location") syncs immediately.
  const [text, setText] = useState(value ? cityLabel(value) : "");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    setText(value ? cityLabel(value) : "");
  }, [value]);

  // Close the popover when focus leaves the entire field (input + list).
  // Using a focusout listener on the wrapper avoids the classic "click
  // suggestion → input blurs first → click never registers" bug that comes
  // from naive `onBlur` close handlers.
  useEffect(() => {
    if (!open) return;
    const node = containerRef.current;
    if (!node) return;
    const handler = (e: FocusEvent) => {
      const next = e.relatedTarget as Node | null;
      if (!next || !node.contains(next)) setOpen(false);
    };
    node.addEventListener("focusout", handler);
    return () => node.removeEventListener("focusout", handler);
  }, [open]);

  const matches = useMemo(() => {
    // Don't show the popover when the input already exactly matches a
    // selected city — the user is "done" with this field.
    if (value && text === cityLabel(value)) return [];
    return searchCities(text);
  }, [text, value]);

  const showPopover = open && matches.length > 0;

  const commit = (city: City) => {
    onChange(city);
    setText(cityLabel(city));
    setOpen(false);
    setHighlight(0);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showPopover) {
      if (e.key === "ArrowDown" && matches.length > 0) {
        setOpen(true);
        e.preventDefault();
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => (h + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => (h - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter") {
      const pick = matches[highlight];
      if (pick) {
        e.preventDefault();
        commit(pick);
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <Field label={label} name={name}>
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            id={name}
            name={name}
            type="text"
            autoComplete="off"
            placeholder={placeholder}
            value={text}
            role="combobox"
            aria-expanded={showPopover}
            aria-controls={listboxId}
            aria-autocomplete="list"
            aria-activedescendant={
              showPopover ? `${listboxId}-opt-${highlight}` : undefined
            }
            onChange={(e) => {
              setText(e.target.value);
              setHighlight(0);
              setOpen(true);
              // Typing invalidates a previously committed selection.
              if (value) onChange(null);
            }}
            onFocus={() => {
              if (matches.length > 0) setOpen(true);
            }}
            onKeyDown={onKeyDown}
            className="w-full bg-transparent text-base text-ink placeholder:text-ink-4 focus:outline-none"
          />
          {trailing}
        </div>
      </Field>

      {showPopover && (
        <div className="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-xl bg-paper-3 shadow-[0_18px_36px_-18px_rgba(15,23,42,0.25)] ring-1 ring-rule">
          <ScrollArea className="max-h-64">
            <ul
              id={listboxId}
              role="listbox"
              className="flex flex-col py-1"
            >
              {matches.map((c, i) => {
                const active = i === highlight;
                return (
                  <li
                    key={c.id}
                    id={`${listboxId}-opt-${i}`}
                    role="option"
                    aria-selected={active}
                    onMouseEnter={() => setHighlight(i)}
                    onMouseDown={(e) => {
                      // mousedown (not click) so the input doesn't blur
                      // and close the popover before the click resolves.
                      e.preventDefault();
                      commit(c);
                    }}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-3 px-4 py-2 text-sm transition-colors",
                      active
                        ? "bg-ink text-paper-3"
                        : "text-ink hover:bg-paper-2",
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    <span
                      className={cn(
                        "text-xs",
                        active ? "text-paper-3/70" : "text-ink-4",
                      )}
                    >
                      {c.state}
                    </span>
                  </li>
                );
              })}
            </ul>
          </ScrollArea>
        </div>
      )}
    </div>
  );
}

/* ------------------------------ Field -------------------------------- */

function Field({
  label,
  name,
  children,
}: {
  label: string;
  name: string;
  children: React.ReactNode;
}) {
  return (
    <label htmlFor={name} className="flex flex-col gap-1">
      <span className="text-xs font-medium text-ink-3">{label}</span>
      <div className="rounded-lg border border-rule bg-paper-3 px-3 py-2 focus-within:border-ink">
        {children}
      </div>
    </label>
  );
}

/* ------------------------------ Icons -------------------------------- */

function Crosshair() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
    >
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1v3M8 12v3M1 8h3M12 8h3" strokeLinecap="round" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg
      width="14"
      height="16"
      viewBox="0 0 14 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      className="text-ink-3"
    >
      <path d="M7 15s5-5.2 5-9A5 5 0 1 0 2 6c0 3.8 5 9 5 9Z" />
      <circle cx="7" cy="6" r="2" fill="currentColor" />
    </svg>
  );
}

function DiamondIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 0 L12 6 L6 12 L0 6 Z" />
    </svg>
  );
}

function SwapIcon() {
  return (
    <svg
      width="11"
      height="11"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 2v7M1.5 7.5 3 9l1.5-1.5" />
      <path d="M9 10V3M7.5 4.5 9 3l1.5 1.5" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      className="animate-spin"
      aria-hidden
    >
      <path d="M7 1.5a5.5 5.5 0 1 1-5.5 5.5" />
    </svg>
  );
}

/* ------------------------------ Helpers ------------------------------ */

/**
 * Re-render on a wall-clock tick. Used by the footer clock. Returns
 * null until the first client-side effect runs so SSR and client render
 * match (Next.js hydration otherwise flags the differing timestamp).
 */
function useNowTick(intervalMs: number): Date | null {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function haversineMiles(
  a: { lat: number; lon: number },
  b: { lat: number; lon: number },
): number {
  const R = 3958.7613; // mean Earth radius in miles
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(s)));
}

/**
 * Rough highway ETA from great-circle distance. 55 mph average roughly
 * matches FL interstate door-to-door once you count the first/last mile
 * surface streets; good enough for a landing-form estimate that the real
 * router will refine on the trip page.
 */
function driveMinutesFor(miles: number): number {
  const avgMph = 55;
  return Math.max(1, Math.round((miles / avgMph) * 60));
}

function formatDuration(mins: number): string {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function formatHHMM(d: Date): string {
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function formatClock(d: Date): string {
  return `${formatHHMM(d)} local`;
}

function formatDateTimeLocal(d: Date): string {
  const y = d.getFullYear();
  const mo = pad2(d.getMonth() + 1);
  const da = pad2(d.getDate());
  const hh = pad2(d.getHours());
  const mm = pad2(d.getMinutes());
  return `${y}-${mo}-${da}T${hh}:${mm}`;
}

function parseDateTimeLocal(s: string): Date | null {
  if (!s) return null;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

function nearestQuarterHour(d: Date): Date {
  const out = new Date(d);
  out.setSeconds(0, 0);
  const m = out.getMinutes();
  const bump = (15 - (m % 15)) % 15;
  // If we're already on a boundary, jump forward 15 min so the default
  // never reads as "depart right now, 0 min away" for a pre-trip tool.
  out.setMinutes(m + (bump === 0 ? 15 : bump));
  return out;
}

type QuickDepartKind = "now" | "plus1h" | "tonight" | "tomorrow";

const QUICK_DEPART: ReadonlyArray<{ kind: QuickDepartKind; label: string }> = [
  { kind: "now", label: "Now" },
  { kind: "plus1h", label: "+1h" },
  { kind: "tonight", label: "Tonight 18:00" },
  { kind: "tomorrow", label: "Tomorrow 08:00" },
];

function computeQuickDepart(kind: QuickDepartKind, ref: Date): Date {
  const d = new Date(ref);
  switch (kind) {
    case "now":
      return nearestQuarterHour(d);
    case "plus1h":
      return nearestQuarterHour(new Date(d.getTime() + 60 * 60_000));
    case "tonight": {
      // If it's already past 18:00 today, advance to tomorrow 18:00 so the
      // chip never sets a time in the past.
      const t = new Date(d);
      t.setSeconds(0, 0);
      t.setHours(18, 0);
      if (t.getTime() <= d.getTime()) t.setDate(t.getDate() + 1);
      return t;
    }
    case "tomorrow": {
      const t = new Date(d);
      t.setSeconds(0, 0);
      t.setDate(t.getDate() + 1);
      t.setHours(8, 0);
      return t;
    }
  }
}

/**
 * Rough FL sunset time, returned as minutes-since-local-midnight.
 *
 * Used only for the landing-form "drives X min after sunset" hint; the
 * trip page gets the real `pysolar` value from the backend. Monthly
 * approximations drift by ~20 min within a month but stay well within
 * the tolerance of a one-liner shown beside a ~55 mph ETA.
 */
function approxFLSunsetMinutes(d: Date): number {
  // 0=Jan … 11=Dec, values are "HH*60+MM" of sunset roughly mid-month
  // for central Florida, with DST baked in where it applies (Mar-Nov).
  const table = [
    17 * 60 + 45, // Jan
    18 * 60 + 10, // Feb
    19 * 60 + 25, // Mar (post-DST)
    19 * 60 + 50, // Apr
    20 * 60 + 10, // May
    20 * 60 + 25, // Jun
    20 * 60 + 25, // Jul
    20 * 60 + 0, // Aug
    19 * 60 + 20, // Sep
    18 * 60 + 40, // Oct
    17 * 60 + 45, // Nov
    17 * 60 + 35, // Dec
  ] as const;
  return table[d.getMonth()] ?? 18 * 60;
}
