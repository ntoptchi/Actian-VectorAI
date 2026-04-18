import Link from "next/link";

import { BackendError, fetchTripBrief } from "~/lib/api";
import type { TripBriefResponse } from "~/lib/types";

type SearchParams = Record<string, string | string[] | undefined>;

function num(v: string | string[] | undefined): number | null {
  if (typeof v !== "string") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmtMin(total: number): string {
  const h = Math.floor(total / 60);
  const m = Math.round(total % 60);
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

function fmtKm(km: number): string {
  return `${km.toFixed(0)} km`;
}

function fmtIso(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

export default async function BriefPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const olat = num(params.olat);
  const olon = num(params.olon);
  const dlat = num(params.dlat);
  const dlon = num(params.dlon);
  const depart = typeof params.depart === "string" ? params.depart : undefined;

  if (olat === null || olon === null || dlat === null || dlon === null) {
    return (
      <Shell>
        <p className="text-red-300">
          Missing or invalid coordinates. Go back and fill them in.
        </p>
        <Link href="/" className="text-indigo-300 underline">
          Back to home
        </Link>
      </Shell>
    );
  }

  let brief: TripBriefResponse | null = null;
  let error: string | null = null;
  try {
    brief = await fetchTripBrief({
      origin: { lat: olat, lon: olon },
      destination: { lat: dlat, lon: dlon },
      timestamp: depart ? new Date(depart).toISOString() : null,
    });
  } catch (e) {
    if (e instanceof BackendError) {
      error = `Backend error (${e.status}): ${e.message}`;
    } else if (e instanceof Error) {
      error = `Could not reach the RouteWise backend: ${e.message}`;
    } else {
      error = "Unknown error contacting the backend.";
    }
  }

  if (error || !brief) {
    return (
      <Shell>
        <h1 className="text-2xl font-semibold">Trip briefing</h1>
        <p className="text-red-300">{error}</p>
        <p className="text-sm text-slate-400">
          Is the FastAPI backend running on port 8000? Try{" "}
          <code>./start.sh</code> from the repo root.
        </p>
        <Link href="/" className="text-indigo-300 underline">
          Back to home
        </Link>
      </Shell>
    );
  }

  const { route, conditions_banner, fatigue_plan, hotspots, pre_trip_checklist } =
    brief;
  const distanceKm = route.distance_m / 1000;

  return (
    <Shell>
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-extrabold tracking-tight">
          Trip briefing
        </h1>
        <p className="text-sm text-slate-400">
          {olat.toFixed(4)},{olon.toFixed(4)} {"->"} {dlat.toFixed(4)},{dlon.toFixed(4)}
        </p>
      </header>

      <section className="grid grid-cols-2 gap-3 rounded-xl bg-slate-800/40 p-5 sm:grid-cols-4">
        <Stat label="Distance" value={fmtKm(distanceKm)} />
        <Stat label="Duration" value={fmtMin(route.duration_s / 60)} />
        <Stat label="Departure" value={fmtIso(route.departure_iso)} />
        <Stat label="Arrival" value={fmtIso(route.arrival_iso)} />
      </section>

      <section className="rounded-xl bg-amber-500/10 p-5 ring-1 ring-amber-400/30">
        <h2 className="mb-2 text-lg font-semibold text-amber-200">
          Tonight&apos;s conditions
        </h2>
        <p className="text-amber-100">{conditions_banner.summary}</p>
        {conditions_banner.dark_drive_minutes > 0 && (
          <p className="mt-2 text-sm text-amber-200/80">
            ~{fmtMin(conditions_banner.dark_drive_minutes)} after dark.
            Sunset at {fmtIso(conditions_banner.sunset_iso)}.
          </p>
        )}
      </section>

      <section className="rounded-xl bg-slate-800/40 p-5">
        <h2 className="mb-3 text-lg font-semibold">Hotspots</h2>
        {hotspots.length === 0 ? (
          <p className="text-sm text-slate-400">
            No hotspots returned for this route. This is the spec&apos;s honesty
            test (s2.4): with the vector DB empty or down, the briefing card
            count is zero. Once you ingest data with{" "}
            <code>scripts/seed_synthetic.py</code> (or real FARS / FDOT / CISS),
            pins will appear here.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {hotspots.map((h) => (
              <li
                key={h.hotspot_id}
                className="flex flex-col gap-1 rounded-lg bg-slate-900/40 p-4"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-semibold">{h.label}</span>
                  <span className="text-xs text-slate-400">
                    {fmtKm(h.km_into_trip)} in - {h.n_crashes} crash
                    {h.n_crashes === 1 ? "" : "es"}
                  </span>
                </div>
                <p className="text-sm text-slate-200">{h.coaching_line}</p>
                {h.intensity_ratio !== null && (
                  <p className="text-xs text-slate-400">
                    {h.intensity_ratio.toFixed(1)}x the FL baseline rate at AADT{" "}
                    {h.aadt?.toLocaleString() ?? "?"}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl bg-slate-800/40 p-5">
        <h2 className="mb-3 text-lg font-semibold">Fatigue plan</h2>
        <p className="text-sm text-slate-400">
          Total drive: {fmtMin(fatigue_plan.total_drive_minutes)}
        </p>
        {fatigue_plan.suggested_stops.length > 0 && (
          <ul className="mt-2 flex flex-col gap-2">
            {fatigue_plan.suggested_stops.map((s, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">{s.label}</span>
                <span className="text-slate-400">
                  {" "}
                  - ETA {fmtIso(s.eta_iso)} ({fmtKm(s.km_into_trip)} in)
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl bg-slate-800/40 p-5">
        <h2 className="mb-3 text-lg font-semibold">Before you go</h2>
        <ul className="list-disc pl-5 text-sm">
          {pre_trip_checklist.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      </section>

      <Link href="/" className="text-indigo-300 underline">
        Plan another trip
      </Link>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center bg-gradient-to-b from-slate-950 to-slate-900 px-4 py-12 text-slate-100">
      <div className="container flex max-w-3xl flex-col gap-6">{children}</div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-400">
        {label}
      </span>
      <span className="text-base font-semibold">{value}</span>
    </div>
  );
}
