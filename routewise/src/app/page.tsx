import Link from "next/link";

import { PlanCard } from "~/components/PlanCard";
import { SiteHeader } from "~/components/SiteHeader";

const DEMO_TRIPS = [
  {
    slug: "miami-tampa",
    eyebrow: "Higher risk · Storms",
    eyebrowTone: "alert" as const,
    title: "Miami to Tampa",
    duration: "4h 12m",
    distance: "280 miles",
    advisory:
      "Heads-up: heavy rain and low visibility on I-75 through Alligator Alley tonight.",
    olat: 25.7617,
    olon: -80.1918,
    dlat: 27.9506,
    dlon: -82.4572,
  },
  {
    slug: "jax-pensacola",
    eyebrow: "Watch out · Dark stretches",
    eyebrowTone: "warn" as const,
    title: "Jacksonville to Pensacola",
    duration: "5h 45m",
    distance: "355 miles",
    advisory:
      "Long dark stretches on I-10 with limited services. Plan a rest stop around Tallahassee.",
    olat: 30.3322,
    olon: -81.6557,
    dlat: 30.4213,
    dlon: -87.2169,
  },
  {
    slug: "orlando-tampa",
    eyebrow: "Lower risk · Clear",
    eyebrowTone: "good" as const,
    title: "Orlando to Tampa",
    duration: "1h 25m",
    distance: "85 miles",
    advisory:
      "Straightforward daylight drive on I-4. A couple of known bottlenecks near Lakeland.",
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
        <SiteFooter />
      </main>
    </div>
  );
}

/* ------------------------------ Hero --------------------------------- */

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="relative mx-auto grid max-w-[1400px] gap-8 px-4 pb-12 pt-10 sm:gap-12 sm:px-6 sm:pb-20 sm:pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pt-20">
        <div className="flex flex-col">
          <span className="anim-in anim-in-1 inline-flex w-fit items-center gap-2 rounded-full bg-paper-2 px-3 py-1 text-xs font-medium text-ink-3">
            <span className="h-1.5 w-1.5 rounded-full bg-good" />
            Pre-trip safety check · no signup
          </span>

          <h1 className="display anim-in anim-in-2 mt-6 text-[clamp(2.5rem,5.5vw,4.5rem)]">
            Know the road before
            <br />
            you drive it.
          </h1>

          <p className="anim-in anim-in-3 mt-3 max-w-md text-base leading-relaxed text-ink-3">
            A quick heads-up on weather, dark stretches, and crash hotspots
            for your drive — so you&apos;re not figuring them out at
            70&nbsp;mph. Built for long drives you haven&apos;t done before.
          </p>

          <div className="anim-in anim-in-4 mt-4 flex flex-col gap-2">
            <span className="text-xs font-medium text-ink-3">
              Two real Florida drives
            </span>
            <div className="grid max-w-xl gap-3 sm:grid-cols-2">
              <CompactTripCard trip={DEMO_TRIPS[0]!} />
              <CompactTripCard trip={DEMO_TRIPS[1]!} />
            </div>
          </div>
        </div>

        <div className="anim-in anim-in-5">
          <PlanCard />
        </div>
      </div>
    </section>
  );
}

const COMPACT_HEADLINE: Record<"alert" | "warn" | "good", string> = {
  alert: "Higher risk · storms tonight",
  warn: "Watch out · dark stretches ahead",
  good: "Lower risk · clear day",
};

function CompactTripCard({ trip }: { trip: (typeof DEMO_TRIPS)[number] }) {
  const shortTitle = trip.title.replace(/\s+to\s+/i, " → ");
  return (
    <Link
      href={tripHref(trip)}
      className="group flex flex-col overflow-hidden rounded-xl bg-paper-3 ring-1 ring-rule transition hover:-translate-y-0.5 hover:ring-ink"
    >
      <div className="h-[120px] w-full overflow-hidden" aria-hidden>
        <PresetArt slug={trip.slug} />
      </div>
      <div className="flex flex-col gap-1.5 p-4">
        <span className="text-sm font-semibold text-ink">{shortTitle}</span>
        <span className="text-xs text-ink-3">
          {COMPACT_HEADLINE[trip.eyebrowTone]}
        </span>
        <span className="mt-2 text-xs font-medium text-ink">
          See sample briefing{" "}
          <span className="inline-block transition-transform group-hover:translate-x-0.5">
            →
          </span>
        </span>
      </div>
    </Link>
  );
}

/* ---------------------------- Feature pair --------------------------- */

function FeaturePair() {
  return (
    <section className="border-y border-rule bg-paper-2">
      <div className="mx-auto grid max-w-[1400px] gap-8 px-4 py-10 sm:gap-12 sm:px-6 sm:py-16 lg:grid-cols-2">
        <div className="grid gap-4 sm:grid-cols-2">
          <FeatureCard
            title="Where crashes actually happen"
            body="We pull real crash reports for your route in conditions like tonight — not a guess, not a heatmap."
            icon={<SparkIcon />}
          />
          <FeatureCard
            title="Weather along your drive"
            body="Rain, fog, and sunset checked at points along your route — not just at the start and end."
            icon={<DropletIcon />}
          />
        </div>

        <div className="flex flex-col gap-5">
          <span className="eyebrow">How it works</span>
          <h2 className="display text-3xl sm:text-4xl">
            A 30-second read before you drive.
          </h2>
          <p className="text-base leading-relaxed text-ink-3">
            You paste your trip in. We find the stretches where crashes
            tend to happen in weather like yours, and give you a short
            heads-up for each one. You close the tab and drive.
          </p>

          <ol className="mt-1 flex flex-col gap-3 text-sm text-ink">
            <NumberedStep n={1}>
              Tell us where you&apos;re driving and when you&apos;re leaving.
            </NumberedStep>
            <NumberedStep n={2}>
              We show weather, dark stretches, and risky spots on your route.
            </NumberedStep>
            <NumberedStep n={3}>
              Each spot gets a one-line &ldquo;what to watch for.&rdquo;
            </NumberedStep>
          </ol>
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  title,
  body,
  icon,
}: {
  title: string;
  body: string;
  icon: React.ReactNode;
}) {
  return (
    <article className="flex flex-col gap-4 rounded-xl bg-paper-3 p-5 ring-1 ring-rule">
      <span className="grid h-9 w-9 place-items-center rounded-lg bg-paper-2 text-ink">
        {icon}
      </span>
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
    <li className="flex items-start gap-3">
      <span className="mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-full bg-ink text-xs font-semibold text-paper">
        {n}
      </span>
      <span className="text-ink">{children}</span>
    </li>
  );
}

/* ---------------------------- Preset art ----------------------------- */
/**
 * Shared SVG scene for the compact preview cards.
 *
 * All variants share the same frame so they read as a set:
 *   - viewBox 400x240
 *   - horizon at y=170
 *   - identical one-point-perspective road below the horizon
 *   - identical "sky object" region at the upper right (cx=315, cy=60)
 *
 * Only the sky gradient + atmospheric flourish swap per slug (rain
 * streaks, stars+moon, sun+clouds).
 */
function PresetArt({ slug }: { slug: string }) {
  return (
    <svg
      viewBox="0 0 400 240"
      className="h-full w-full"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id="sky-storm" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1a3160" />
          <stop offset="1" stopColor="#070d1d" />
        </linearGradient>
        <linearGradient id="sky-night" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#18325d" />
          <stop offset="1" stopColor="#0a1735" />
        </linearGradient>
        <linearGradient id="sky-clear" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#bfd9ed" />
          <stop offset="1" stopColor="#7ca8cc" />
        </linearGradient>
      </defs>

      <rect
        width="400"
        height="170"
        fill={
          slug === "miami-tampa"
            ? "url(#sky-storm)"
            : slug === "jax-pensacola"
              ? "url(#sky-night)"
              : "url(#sky-clear)"
        }
      />

      <SkyAtmosphere slug={slug} />

      <line
        x1="0"
        y1="170"
        x2="400"
        y2="170"
        stroke="#000"
        strokeOpacity="0.28"
      />

      <polygon points="-20,240 420,240 220,170 180,170" fill="#0a1220" />

      <g stroke="#f8fafc" strokeOpacity="0.45" strokeLinecap="round">
        <line x1="-20" y1="240" x2="180" y2="170" strokeWidth="1.25" />
        <line x1="420" y1="240" x2="220" y2="170" strokeWidth="1.25" />
      </g>

      <g fill="#f8fafc" opacity="0.88">
        <rect x="198" y="172" width="4" height="2.5" />
        <rect x="195" y="183" width="10" height="3.5" />
        <rect x="190" y="198" width="20" height="5" />
        <rect x="182" y="218" width="36" height="7" />
      </g>
    </svg>
  );
}

function SkyAtmosphere({ slug }: { slug: string }) {
  if (slug === "miami-tampa") {
    return (
      <>
        <g stroke="#c6d4ec" strokeOpacity="0.22" strokeWidth="1.2">
          {Array.from({ length: 22 }).map((_, i) => (
            <line
              key={i}
              x1={i * 22 - 40}
              y1="0"
              x2={i * 22 - 90}
              y2="170"
            />
          ))}
        </g>
        <ellipse
          cx="315"
          cy="60"
          rx="70"
          ry="22"
          fill="#0a1735"
          opacity="0.55"
        />
        <ellipse
          cx="270"
          cy="72"
          rx="55"
          ry="16"
          fill="#0a1735"
          opacity="0.4"
        />
      </>
    );
  }
  if (slug === "jax-pensacola") {
    return (
      <>
        {Array.from({ length: 24 }).map((_, i) => {
          const cx = (i * 53) % 400;
          const cy = 15 + ((i * 37) % 130);
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r="0.9"
              fill="#f8fafc"
              opacity={0.55}
            />
          );
        })}
        <circle cx="315" cy="60" r="20" fill="#f8fafc" />
        <circle cx="307" cy="55" r="20" fill="#0a1735" />
      </>
    );
  }
  return (
    <>
      <circle cx="315" cy="60" r="22" fill="#fbfbfb" opacity="0.95" />
      <path
        d="M40 70 C 80 65, 120 78, 170 70"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.6"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M200 100 C 240 95, 270 106, 310 98"
        fill="none"
        stroke="#ffffff"
        strokeOpacity="0.45"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </>
  );
}

/* ----------------------------- Footer -------------------------------- */

function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-paper-2">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-2 px-6 py-8 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between">
        <span>
          RouteWise · a pre-trip safety check for new drivers. Florida
          only.
        </span>
        <span className="text-ink-4">
          Not a nav app. Don&apos;t read while driving.
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

