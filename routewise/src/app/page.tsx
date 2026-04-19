import Link from "next/link";

import { PlanCard } from "~/components/PlanCard";
import { SiteHeader } from "~/components/SiteHeader";

const DEMO_TRIPS = [
  {
    slug: "miami-tampa",
    eyebrow: "High Risk · Stormy",
    eyebrowTone: "alert" as const,
    title: "Miami to Tampa",
    duration: "4h 12m",
    distance: "280 miles",
    advisory:
      "Safety re-rank: rerouting via Highway 27 to avoid I-75 flood alerts.",
    olat: 25.7617,
    olon: -80.1918,
    dlat: 27.9506,
    dlon: -82.4572,
  },
  {
    slug: "jax-pensacola",
    eyebrow: "Medium Risk · Night",
    eyebrowTone: "warn" as const,
    title: "Jacksonville to Pensacola",
    duration: "5h 45m",
    distance: "355 miles",
    advisory:
      "Advisory: extended dark zones. Optimal fuel stops calculated for wildlife passes.",
    olat: 30.3322,
    olon: -81.6557,
    dlat: 30.4213,
    dlon: -87.2169,
  },
  {
    slug: "orlando-tampa",
    eyebrow: "Low Risk · Standard",
    eyebrowTone: "good" as const,
    title: "Orlando to Tampa",
    duration: "1h 25m",
    distance: "85 miles",
    advisory:
      "Optimal conditions. Direct routing via I-4 recommended with no delays.",
    olat: 28.5383,
    olon: -81.3792,
    dlat: 27.9506,
    dlon: -82.4572,
  },
];

function tripHref(t: (typeof DEMO_TRIPS)[number]): string {
  const params = new URLSearchParams({
    olat: String(t.olat),
    olon: String(t.olon),
    dlat: String(t.dlat),
    dlon: String(t.dlon),
  });
  return `/trip?${params.toString()}`;
}

export default function Home() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader active="explore" />

      <main>
        <Hero />
        <FeaturePair />
        <AlgorithmConcept />
        <AdvisoryRoutes />
        <SiteFooter />
      </main>
    </div>
  );
}

/* ------------------------------ Hero --------------------------------- */

function Hero() {
  return (
    <section className="relative overflow-hidden bg-paper-grain">
      {/* Topographic line decoration in the background — pure SVG, no asset. */}
      <TopoBackdrop />

      <div className="relative mx-auto grid max-w-[1400px] gap-12 px-6 pb-24 pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pt-28">
        <div className="flex flex-col gap-8">
          <span className="eyebrow eyebrow-rule max-w-[18rem]">
            <span>Intelligent Navigation</span>
          </span>

          <h1 className="display text-[clamp(3rem,7vw,6.25rem)]">
            Safety is the
            <br />
            New Shortest
            <br />
            Path.
          </h1>

          <p className="max-w-md text-base leading-relaxed text-ink-3">
            Don&apos;t just get there faster. Get there safer. RouteWise analyzes
            real-time weather, accident hotspots, and road conditions to
            re-rank your commute.
          </p>
        </div>

        <PlanCard />
      </div>
    </section>
  );
}

function TopoBackdrop() {
  return (
    <svg
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.18]"
      preserveAspectRatio="none"
      viewBox="0 0 1400 700"
    >
      <defs>
        <linearGradient id="topo-fade" x1="0" x2="1">
          <stop offset="0" stopColor="#0b1f44" stopOpacity="0.0" />
          <stop offset="0.6" stopColor="#0b1f44" stopOpacity="0.6" />
          <stop offset="1" stopColor="#0b1f44" stopOpacity="0.0" />
        </linearGradient>
      </defs>
      <g fill="none" stroke="url(#topo-fade)" strokeWidth="1">
        {Array.from({ length: 14 }).map((_, i) => {
          const dy = i * 36;
          return (
            <path
              key={i}
              d={`M-50 ${120 + dy} C 250 ${60 + dy}, 520 ${220 + dy}, 780 ${
                140 + dy
              } S 1320 ${60 + dy}, 1500 ${180 + dy}`}
            />
          );
        })}
      </g>
    </svg>
  );
}

/* ---------------------------- Feature pair --------------------------- */

function FeaturePair() {
  return (
    <section className="border-y border-rule bg-paper-2">
      <div className="mx-auto grid max-w-[1400px] gap-12 px-6 py-20 lg:grid-cols-2">
        <div className="grid gap-6 sm:grid-cols-2">
          <FeatureCard
            tag="ai"
            title="Predictive Risk"
            body="ML-driven analysis of historical accident spikes during specific weather windows."
            icon={<SparkIcon />}
          />
          <FeatureCard
            tag="geo"
            title="Hyper-Local"
            body="Road-level weather data that traditional GPS apps ignore for route calculation."
            icon={<DropletIcon />}
          />
        </div>

        <div className="flex flex-col gap-6">
          <span className="eyebrow">The Algorithm</span>
          <h2 className="display text-4xl sm:text-5xl">
            The Safety Re-ranker Concept.
          </h2>
          <p className="text-base leading-relaxed text-ink-3">
            Most navigation apps optimize for the fastest route by default.
            Our proprietary{" "}
            <span className="font-semibold text-ink">Safety Re-ranker</span>{" "}
            puts risk at the top of the hierarchy. If a route is 2 minutes
            faster but includes a flooded underpass or a high-accident
            interchange, we re-rank the safer alternative to #1.
          </p>

          <ol className="mt-2 flex flex-col gap-3 text-sm text-ink">
            <NumberedStep n={1}>
              Avoidance of high-accident hotspots
            </NumberedStep>
            <NumberedStep n={2}>
              Real-time visibility and drainage scoring
            </NumberedStep>
            <NumberedStep n={3}>
              Per-segment re-ranking against a cost function
            </NumberedStep>
          </ol>
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  tag,
  title,
  body,
  icon,
}: {
  tag: string;
  title: string;
  body: string;
  icon: React.ReactNode;
}) {
  return (
    <article className="flex flex-col justify-between gap-6 rounded-sm bg-paper-3 p-6 ring-1 ring-rule">
      <div className="flex items-start justify-between">
        <span className="grid h-9 w-9 place-items-center rounded-sm bg-paper text-ink">
          {icon}
        </span>
        <span className="eyebrow text-[0.625rem]">{tag}</span>
      </div>
      <div className="flex flex-col gap-1.5">
        <h3 className="text-base font-semibold text-ink">{title}</h3>
        <p className="text-sm leading-relaxed text-ink-3">{body}</p>
      </div>
    </article>
  );
}

function NumberedStep({
  n,
  children,
}: {
  n: number;
  children: React.ReactNode;
}) {
  return (
    <li className="flex items-center gap-3">
      <span className="grid h-7 w-7 place-items-center rounded-sm bg-ink text-xs font-semibold text-paper">
        {n}
      </span>
      <span className="text-ink">{children}</span>
    </li>
  );
}

/* ------------------------- Algorithm concept ------------------------- */
/* (folded into FeaturePair above to match the mockup composition) */
function AlgorithmConcept() {
  return null;
}

/* -------------------------- Advisory routes -------------------------- */

function AdvisoryRoutes() {
  return (
    <section id="hotspots" className="bg-paper">
      <div className="mx-auto max-w-[1400px] px-6 py-20">
        <div className="mb-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="display text-3xl sm:text-4xl">Active Advisory Routes</h2>
            <p className="text-sm text-ink-3">
              Explore how RouteWise adjusts for environmental variables.
            </p>
          </div>
          <span className="eyebrow flex items-center gap-2">
            See all presets
            <ArrowRight />
          </span>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {DEMO_TRIPS.map((t) => (
            <TripPresetCard key={t.slug} trip={t} />
          ))}
        </div>
      </div>
    </section>
  );
}

const TONE_BG: Record<"alert" | "warn" | "good", string> = {
  alert: "bg-alert text-paper",
  warn: "bg-gold text-paper",
  good: "bg-good text-paper",
};

function TripPresetCard({ trip }: { trip: (typeof DEMO_TRIPS)[number] }) {
  return (
    <Link
      href={tripHref(trip)}
      className="group flex flex-col overflow-hidden rounded-sm bg-paper-3 ring-1 ring-rule transition hover:ring-ink"
    >
      <div
        className="relative aspect-[5/3] w-full overflow-hidden"
        aria-hidden
      >
        <PresetArt slug={trip.slug} />
        <div className="absolute left-3 top-3 flex items-center gap-1.5">
          <span
            className={`flex items-center gap-1 rounded-sm px-2 py-1 text-[0.6875rem] font-semibold uppercase tracking-[0.1em] ${TONE_BG[trip.eyebrowTone]}`}
          >
            <Triangle />
            {trip.eyebrow.split("·")[0]?.trim()}
          </span>
          <span className="rounded-sm bg-ink/80 px-2 py-1 text-[0.6875rem] font-medium uppercase tracking-[0.1em] text-paper">
            {trip.eyebrow.split("·")[1]?.trim()}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-4 p-5">
        <h3 className="font-display text-xl font-medium text-ink">
          {trip.title}
        </h3>
        <div className="flex items-center gap-3 text-xs text-ink-3">
          <Clock />
          <span>{trip.duration}</span>
          <span className="h-1 w-1 rounded-full bg-ink-4" />
          <span>{trip.distance}</span>
        </div>

        <p
          className={`rounded-sm px-3 py-2 text-xs leading-relaxed ${
            trip.eyebrowTone === "alert"
              ? "bg-alert-2 text-alert"
              : trip.eyebrowTone === "warn"
                ? "bg-gold/15 text-gold"
                : "bg-good/10 text-good"
          }`}
        >
          {trip.advisory}
        </p>

        <span className="mt-1 inline-flex w-full items-center justify-center rounded-sm border border-rule py-2.5 text-xs font-semibold uppercase tracking-[0.12em] text-ink transition group-hover:border-ink group-hover:bg-ink group-hover:text-paper">
          Preview Route
        </span>
      </div>
    </Link>
  );
}

/** SVG-only "photographic" placeholder so the cards work without assets. */
function PresetArt({ slug }: { slug: string }) {
  if (slug === "miami-tampa") {
    return (
      <svg viewBox="0 0 400 240" className="h-full w-full">
        <defs>
          <linearGradient id="storm" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0b1f44" />
            <stop offset="0.5" stopColor="#1a3160" />
            <stop offset="1" stopColor="#070d1d" />
          </linearGradient>
        </defs>
        <rect width="400" height="240" fill="url(#storm)" />
        {Array.from({ length: 18 }).map((_, i) => (
          <line
            key={i}
            x1={i * 24 - 30}
            y1="0"
            x2={i * 24 - 80}
            y2="240"
            stroke="#e6c372"
            strokeOpacity="0.18"
            strokeWidth="1.2"
          />
        ))}
        <circle cx="320" cy="60" r="40" fill="#1a3160" opacity="0.6" />
      </svg>
    );
  }
  if (slug === "jax-pensacola") {
    return (
      <svg viewBox="0 0 400 240" className="h-full w-full">
        <defs>
          <linearGradient id="night" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#13284f" />
            <stop offset="1" stopColor="#0b1f44" />
          </linearGradient>
        </defs>
        <rect width="400" height="240" fill="url(#night)" />
        <path
          d="M0 200 C 100 160, 180 220, 260 170 S 400 140, 420 180 L 420 240 L 0 240 Z"
          fill="#0a1735"
        />
        {Array.from({ length: 30 }).map((_, i) => (
          <circle
            key={i}
            cx={(i * 53) % 400}
            cy={(i * 37) % 140 + 20}
            r="0.9"
            fill="#e6c372"
            opacity={0.6}
          />
        ))}
        <line
          x1="40"
          y1="190"
          x2="360"
          y2="160"
          stroke="#e6c372"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 400 240" className="h-full w-full">
      <defs>
        <linearGradient id="day" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#cfe5f5" />
          <stop offset="1" stopColor="#9bc4e2" />
        </linearGradient>
      </defs>
      <rect width="400" height="240" fill="url(#day)" />
      <path d="M0 180 L 400 180 L 400 240 L 0 240 Z" fill="#3a4a6b" />
      <path d="M0 180 L 400 180" stroke="#0b1f44" strokeWidth="1" />
      {Array.from({ length: 8 }).map((_, i) => (
        <rect
          key={i}
          x={40 + i * 45}
          y={184}
          width="20"
          height="3"
          fill="#fbf6ec"
        />
      ))}
      <circle cx="80" cy="60" r="22" fill="#fbf6ec" />
    </svg>
  );
}

/* ----------------------------- Footer -------------------------------- */

function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-paper-2">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-2 px-6 py-8 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between">
        <span>
          RouteWise · re-ranking driving routes by crash risk · powered by
          Actian VectorAI DB
        </span>
        <span className="font-mono text-[0.6875rem] uppercase tracking-[0.18em]">
          v0.2 · safety re-ranker
        </span>
      </div>
    </footer>
  );
}

/* ------------------------------ Icons -------------------------------- */

function SparkIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
      <path d="M10 1.5l1.5 4.5 4.5 1.5-4.5 1.5L10 13.5l-1.5-4.5L4 7.5l4.5-1.5L10 1.5Z" />
      <circle cx="15.5" cy="14.5" r="1.5" />
    </svg>
  );
}

function DropletIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    >
      <path d="M10 2 C 6 7, 4 10, 4 13 a 6 6 0 0 0 12 0 c 0 -3 -2 -6 -6 -11 Z" />
    </svg>
  );
}

function Triangle() {
  return (
    <svg width="9" height="9" viewBox="0 0 9 9" fill="currentColor">
      <path d="M4.5 0 L9 8 L0 8 Z" />
    </svg>
  );
}

function Clock() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
    >
      <circle cx="6" cy="6" r="5" />
      <path d="M6 3v3l2 1" strokeLinecap="round" />
    </svg>
  );
}

function ArrowRight() {
  return (
    <svg
      width="14"
      height="10"
      viewBox="0 0 14 10"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M1 5h12M9 1l4 4-4 4" />
    </svg>
  );
}
