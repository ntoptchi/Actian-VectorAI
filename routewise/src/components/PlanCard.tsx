"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ScrollArea } from "~/components/ui/scroll-area";
import { CITIES, cityLabel, searchCities, type City } from "~/lib/cities";
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
        const here: City = {
          id: `here-${pos.coords.latitude.toFixed(4)}-${pos.coords.longitude.toFixed(4)}`,
          name: "Current Location",
          state: "—",
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
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

  return (
    <form
      onSubmit={handleSubmit}
      className="relative self-start rounded-sm bg-paper-3 p-7 shadow-[0_30px_60px_-30px_rgba(11,31,68,0.25)] ring-1 ring-rule"
    >
      <span className="eyebrow">Plan Your Safe Route</span>
      <div className="mt-1 h-px w-full bg-rule" />

      <div className="mt-6 flex flex-col gap-5">
        <CityCombobox
          label="Origin"
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
              <Crosshair />
            </button>
          }
        />

        <CityCombobox
          label="Destination"
          name="destination"
          placeholder="Where to?"
          value={destination}
          onChange={setDestination}
          trailing={<PinIcon />}
        />

        <Field label="Depart (date & time)" name="depart">
          <input
            name="depart"
            type="datetime-local"
            value={depart}
            onChange={(e) => setDepart(e.target.value)}
            className="w-full bg-transparent text-base text-ink placeholder:text-ink-4 focus:outline-none"
          />
        </Field>

        {error && (
          <div
            role="alert"
            className="rounded-sm border-l-2 border-alert bg-alert-2/60 px-3 py-2 text-xs text-alert"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          className="mt-2 inline-flex items-center justify-center gap-2 rounded-sm bg-ink py-3.5 text-sm font-semibold uppercase tracking-[0.12em] text-paper transition hover:bg-ink-2"
        >
          <DiamondIcon />
          Find Route
        </button>
        <p className="text-[0.6875rem] uppercase tracking-[0.14em] text-ink-4">
          Florida cities only · {CITIES.length} available
        </p>
      </div>
    </form>
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
        <div className="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-sm bg-paper-3 shadow-[0_18px_36px_-18px_rgba(11,31,68,0.45)] ring-1 ring-rule">
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
                        ? "bg-ink text-paper"
                        : "text-ink hover:bg-paper-2",
                    )}
                  >
                    <span className="truncate">{c.name}</span>
                    <span
                      className={cn(
                        "font-mono text-[0.625rem] uppercase tracking-[0.16em]",
                        active ? "text-paper/70" : "text-ink-4",
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
    <label htmlFor={name} className="flex flex-col gap-1.5">
      <span className="eyebrow text-[0.625rem]">{label}</span>
      <div className="border-b border-rule pb-2">{children}</div>
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
