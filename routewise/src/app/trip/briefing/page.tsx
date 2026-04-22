import Link from "next/link";

import { SiteHeader } from "~/components/SiteHeader";
import { BackendError, fetchTripBrief, parseDepart } from "~/lib/api";
import { nearestCity } from "~/lib/cities";
import type { TripBriefResponse } from "~/lib/types";

import { BriefingView } from "./BriefingView";

type SearchParams = Record<string, string | string[] | undefined>;

function num(v: string | string[] | undefined): number | null {
  if (typeof v !== "string") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * Full pre-trip briefing — the "read before you pull out of the driveway"
 * document. Same query-param contract as /trip so the two views can share
 * a URL; just a longer-form rendering of the same TripBriefResponse.
 */
export default async function BriefingPage({
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
      <Shell title="Missing coordinates">
        <p className="text-sm text-ink-3">
          The briefing needs both an origin and a destination. Head back to the
          home page and plan a trip.
        </p>
        <Link
          href="/"
          className="inline-flex w-fit items-center gap-2 rounded-sm bg-ink px-4 py-2 text-xs font-semibold text-paper transition hover:bg-ink-2"
        >
          ← Back to home
        </Link>
      </Shell>
    );
  }

  const mapHref = tripMapHref({ olat, olon, dlat, dlon, depart });

  let brief: TripBriefResponse | null = null;
  let error: string | null = null;
  try {
    brief = await fetchTripBrief({
      origin: { lat: olat, lon: olon },
      destination: { lat: dlat, lon: dlon },
      timestamp: parseDepart(depart),
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
      <Shell title="Briefing unavailable">
        <div className="rounded-sm border-l-2 border-alert bg-alert-2/60 px-4 py-3 text-sm text-alert">
          {error}
        </div>
        <p className="text-sm text-ink-3">
          Is the FastAPI backend running on port 8080? Try{" "}
          <code className="rounded bg-paper-3 px-1.5 py-0.5 font-mono text-xs">
            ./start.sh
          </code>{" "}
          from the repo root.
        </p>
        <Link
          href={mapHref}
          className="inline-flex w-fit items-center gap-2 rounded-sm bg-ink px-4 py-2 text-xs font-semibold text-paper transition hover:bg-ink-2"
        >
          ← Back to route map
        </Link>
      </Shell>
    );
  }

  // Reverse-derive city names from the URL coordinates so the headline
  // reads "Jacksonville → Pensacola" instead of two lat/lon pairs. When
  // origins come from geolocation (no curated city within ~50 km), fall
  // back to null and BriefingView degrades to a generic headline.
  const originName = nearestCity(olat, olon)?.name ?? null;
  const destName = nearestCity(dlat, dlon)?.name ?? null;

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <SiteHeader active="routes" />
      <BriefingView
        brief={brief}
        originName={originName}
        destName={destName}
        mapHref={mapHref}
      />
    </div>
  );
}

function tripMapHref({
  olat,
  olon,
  dlat,
  dlon,
  depart,
}: {
  olat: number;
  olon: number;
  dlat: number;
  dlon: number;
  depart: string | undefined;
}): string {
  const sp = new URLSearchParams({
    olat: String(olat),
    olon: String(olon),
    dlat: String(dlat),
    dlon: String(dlon),
  });
  if (depart) sp.set("depart", depart);
  return `/trip?${sp.toString()}`;
}

function Shell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-paper">
      <SiteHeader active="routes" />
      <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 pt-20">
        <span className="eyebrow">Safety Briefing</span>
        <h1 className="display text-4xl">{title}</h1>
        {children}
      </main>
    </div>
  );
}
