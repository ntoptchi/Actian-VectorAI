import Link from "next/link";

import { SiteHeader } from "~/components/SiteHeader";

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

  const briefingParams = new URLSearchParams({
    olat: String(olat),
    olon: String(olon),
    dlat: String(dlat),
    dlon: String(dlon),
  });
  if (depart) briefingParams.set("depart", depart);
  const briefingHref = `/trip/briefing?${briefingParams.toString()}`;

  return (
    <div className="flex min-h-screen flex-col bg-paper lg:h-screen lg:overflow-hidden">
      <SiteHeader variant="flush" active="routes" />
      <TripView
        origin={{ lat: olat, lon: olon }}
        destination={{ lat: dlat, lon: dlon }}
        depart={depart}
        briefingHref={briefingHref}
      />
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
      <main className="mx-auto flex max-w-2xl flex-col gap-5 px-4 pt-12 sm:px-6 sm:pt-20">
        <span className="eyebrow">Safety Briefing</span>
        <h1 className="display text-3xl sm:text-4xl">{title}</h1>
        {children}
      </main>
    </div>
  );
}
