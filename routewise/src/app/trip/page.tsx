import Link from "next/link";

import { SiteHeader } from "~/components/SiteHeader";
import { BackendError, fetchTripBrief, parseDepart } from "~/lib/api";
import type { TripBriefResponse } from "~/lib/types";

import { TripView } from "./TripView";

type SearchParams = Record<string, string | string[] | undefined>;

function num(v: string | string[] | undefined): number | null {
  if (typeof v !== "string") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export default async function TripPage({
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
          The trip planner needs both an origin and a destination. Head back to
          the home page and pick a preset.
        </p>
        <Link
          href="/"
          className="inline-flex w-fit items-center gap-2 rounded-sm bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-paper transition hover:bg-ink-2"
        >
          ← Back to home
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
          href="/"
          className="inline-flex w-fit items-center gap-2 rounded-sm bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-paper transition hover:bg-ink-2"
        >
          ← Back to home
        </Link>
      </Shell>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper lg:h-screen lg:overflow-hidden">
      <SiteHeader variant="flush" active="routes" />
      <TripView brief={brief} />
    </div>
  );
}

function Shell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-paper-grain">
      <SiteHeader active="routes" />
      <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 pt-20">
        <span className="eyebrow">Safety Briefing</span>
        <h1 className="display text-4xl">{title}</h1>
        {children}
      </main>
    </div>
  );
}
