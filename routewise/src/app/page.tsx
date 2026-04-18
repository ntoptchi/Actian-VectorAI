import Link from "next/link";

const DEMO_TRIPS = [
  {
    label: "Miami -> Tampa (the hero demo)",
    description: "I-75 / Alligator Alley. Urban, Everglades rural interstate, Gulf metro.",
    olat: 25.7617,
    olon: -80.1918,
    dlat: 27.9506,
    dlon: -82.4572,
  },
  {
    label: "Jacksonville -> Pensacola (fatigue + rural)",
    description: "I-10 across the Panhandle. Long, sparse-services, wildlife.",
    olat: 30.3322,
    olon: -81.6557,
    dlat: 30.4213,
    dlon: -87.2169,
  },
  {
    label: "Orlando -> Tampa (verification demo)",
    description: 'I-4. The "deadliest interstate" — show retrieval surfaces what locals know.',
    olat: 28.5383,
    olon: -81.3792,
    dlat: 27.9506,
    dlon: -82.4572,
  },
];

function buildHref(t: (typeof DEMO_TRIPS)[number]): string {
  const params = new URLSearchParams({
    olat: String(t.olat),
    olon: String(t.olon),
    dlat: String(t.dlat),
    dlon: String(t.dlon),
  });
  return `/brief?${params.toString()}`;
}

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center bg-gradient-to-b from-slate-950 to-slate-900 px-4 py-16 text-slate-100">
      <div className="container flex max-w-3xl flex-col gap-10">
        <header className="flex flex-col gap-3">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
            RouteWise
          </h1>
          <p className="text-lg text-slate-300">
            A pre-trip briefing for unfamiliar long drives. Paste a route and
            we&apos;ll pull the real crashes that have happened on roads like
            yours in conditions like yours.
          </p>
        </header>

        <section className="flex flex-col gap-4 rounded-xl bg-slate-800/40 p-6">
          <h2 className="text-xl font-semibold">Plan a trip</h2>
          <form action="/brief" className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Origin lat
                <input
                  name="olat"
                  type="number"
                  step="any"
                  required
                  defaultValue={25.7617}
                  className="rounded-md bg-slate-900/70 px-3 py-2 text-base"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Origin lon
                <input
                  name="olon"
                  type="number"
                  step="any"
                  required
                  defaultValue={-80.1918}
                  className="rounded-md bg-slate-900/70 px-3 py-2 text-base"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Destination lat
                <input
                  name="dlat"
                  type="number"
                  step="any"
                  required
                  defaultValue={27.9506}
                  className="rounded-md bg-slate-900/70 px-3 py-2 text-base"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                Destination lon
                <input
                  name="dlon"
                  type="number"
                  step="any"
                  required
                  defaultValue={-82.4572}
                  className="rounded-md bg-slate-900/70 px-3 py-2 text-base"
                />
              </label>
            </div>
            <label className="flex flex-col gap-1 text-sm">
              Departure (optional, ISO 8601)
              <input
                name="depart"
                type="datetime-local"
                className="rounded-md bg-slate-900/70 px-3 py-2 text-base"
              />
            </label>
            <button
              type="submit"
              className="mt-2 self-start rounded-md bg-indigo-500 px-5 py-2 font-medium text-white hover:bg-indigo-400"
            >
              Brief me
            </button>
          </form>
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-semibold">Demo trips</h2>
          <div className="flex flex-col gap-3">
            {DEMO_TRIPS.map((t) => (
              <Link
                key={t.label}
                href={buildHref(t)}
                className="flex flex-col gap-1 rounded-lg bg-slate-800/40 p-4 hover:bg-slate-800/70"
              >
                <span className="text-base font-semibold">{t.label}</span>
                <span className="text-sm text-slate-400">{t.description}</span>
              </Link>
            ))}
          </div>
        </section>

        <footer className="text-xs text-slate-500">
          v0.1 groundwork. Backend at <code>{`${"$"}{BACKEND_URL}`}</code> on{" "}
          <code>POST /trip/brief</code>. See <code>ROUTEWISE.md</code> for the
          spec.
        </footer>
      </div>
    </main>
  );
}
