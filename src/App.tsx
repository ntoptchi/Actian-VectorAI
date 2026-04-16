import {
  anomalies,
  incidentMatches,
  insights,
  metrics,
  responseTimeline,
  type Severity,
} from "./data/dashboardData";

const severityStyles: Record<Severity, string> = {
  Critical: "bg-ember/20 text-ember ring-1 ring-ember/30",
  Elevated: "bg-signal/20 text-signal ring-1 ring-signal/30",
  Watching: "bg-surge/20 text-surge ring-1 ring-surge/30",
};

function App() {
  const primaryIncident = incidentMatches[0];

  return (
    <main className="min-h-screen overflow-hidden text-mist">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <section className="relative overflow-hidden rounded-[32px] border border-white/10 bg-white/5 p-6 shadow-glow backdrop-blur-xl sm:p-8">
          <div className="pointer-events-none absolute inset-0 bg-grid bg-[size:42px_42px] opacity-20" />
          <div className="pointer-events-none absolute -left-24 top-0 h-64 w-64 rounded-full bg-signal/20 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 rounded-full bg-ember/10 blur-3xl" />

          <div className="relative z-10">
            <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl animate-rise">
                <p className="mb-3 inline-flex rounded-full border border-surge/30 bg-surge/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.24em] text-surge">
                  Active sensor intelligence dashboard
                </p>
                <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
                  Detect sensor anomalies, match them to prior equipment incidents, and surface the fastest field response.
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-mist/80 sm:text-base">
                  This view compares live telemetry against expected operating ranges, identifies abnormal
                  equipment behavior, and then retrieves historically similar incidents so operators can
                  act on proven corrective actions instead of starting from zero.
                </p>
              </div>

              <div className="grid min-w-full gap-3 sm:grid-cols-2 lg:min-w-[340px] lg:max-w-md">
                {metrics.map((metric, index) => (
                  <article
                    key={metric.label}
                    className="animate-rise rounded-3xl border border-white/10 bg-midnight/70 p-4"
                    style={{ animationDelay: `${index * 120}ms` }}
                  >
                    <p className="text-sm text-mist/70">{metric.label}</p>
                    <div className="mt-3 flex items-end justify-between">
                      <span className="text-3xl font-bold text-white">{metric.value}</span>
                      <span
                        className={`text-sm font-medium ${
                          metric.trend === "up" ? "text-ember" : "text-surge"
                        }`}
                      >
                        {metric.change}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <section className="rounded-[28px] border border-white/10 bg-ink/70 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Anomaly pressure map</h2>
                    <p className="mt-1 text-sm text-mist/70">
                      Current sensor deltas against learned baseline ranges
                    </p>
                  </div>
                  <div className="rounded-full border border-ember/30 bg-ember/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-ember">
                    Escalating
                  </div>
                </div>

                <div className="mt-5 space-y-4">
                  {anomalies.map((anomaly) => (
                    <article
                      key={anomaly.id}
                      className="rounded-3xl border border-white/8 bg-white/5 p-4 transition-transform duration-300 hover:-translate-y-1"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-semibold text-white">{anomaly.metric}</h3>
                            <span className={`rounded-full px-2.5 py-1 text-xs ${severityStyles[anomaly.severity]}`}>
                              {anomaly.severity}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-mist/70">{anomaly.scope}</p>
                        </div>
                        <div className="flex gap-6 text-sm">
                          <div>
                            <p className="text-mist/50">Current</p>
                            <p className="font-semibold text-white">{anomaly.value}</p>
                          </div>
                          <div>
                            <p className="text-mist/50">Expected</p>
                            <p className="font-semibold text-white">{anomaly.expected}</p>
                          </div>
                          <div>
                            <p className="text-mist/50">Deviation</p>
                            <p className="font-semibold text-ember">{anomaly.deviation}</p>
                          </div>
                        </div>
                      </div>
                      <p className="mt-4 text-sm leading-6 text-mist/80">{anomaly.signal}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Closest prior incident</h2>
                    <p className="mt-1 text-sm text-mist/70">Top historical match for the current telemetry pattern</p>
                  </div>
                  <div className="rounded-full border border-surge/30 bg-surge/10 px-3 py-1 text-xs font-medium text-surge">
                    {primaryIncident.similarity}% match
                  </div>
                </div>

                <div className="mt-5 rounded-3xl border border-white/10 bg-midnight/80 p-5">
                  <p className="text-xs uppercase tracking-[0.24em] text-signal">{primaryIncident.id}</p>
                  <h3 className="mt-2 text-2xl font-semibold text-white">{primaryIncident.incident}</h3>
                  <div className="mt-5 space-y-4 text-sm leading-6 text-mist/80">
                    <div>
                      <p className="text-mist/50">Cause</p>
                      <p>{primaryIncident.cause}</p>
                    </div>
                    <div>
                      <p className="text-mist/50">Resolution</p>
                      <p>{primaryIncident.resolution}</p>
                    </div>
                    <div>
                      <p className="text-mist/50">Outcome</p>
                      <p>{primaryIncident.impact}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-5 rounded-3xl border border-white/10 bg-ink/80 p-5">
                  <p className="text-sm font-medium text-white">Recommended action sequence</p>
                  <ol className="mt-4 space-y-4 text-sm text-mist/80">
                    {responseTimeline.map((step, index) => (
                      <li key={step} className="flex gap-3">
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-signal/15 text-xs font-semibold text-signal">
                          {index + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </section>
            </div>

            <div className="mt-6 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
              <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-white">Incident library matches</h2>
                    <p className="mt-1 text-sm text-mist/70">
                      Past equipment incidents ranked by signal similarity and recovery usefulness
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-4">
                  {incidentMatches.map((incident) => (
                    <article
                      key={incident.id}
                      className="rounded-3xl border border-white/10 bg-midnight/60 p-4"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="flex items-center gap-3">
                            <span className="rounded-full border border-signal/30 bg-signal/10 px-2.5 py-1 text-xs text-signal">
                              {incident.id}
                            </span>
                            <span className="text-xs uppercase tracking-[0.2em] text-mist/50">
                              {incident.owner}
                            </span>
                          </div>
                          <h3 className="mt-3 text-lg font-semibold text-white">{incident.incident}</h3>
                        </div>
                        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-white">
                          {incident.similarity}% similar
                        </div>
                      </div>

                      <div className="mt-4 grid gap-4 text-sm leading-6 text-mist/75">
                        <div>
                          <p className="text-mist/50">What happened before</p>
                          <p>{incident.cause}</p>
                        </div>
                        <div>
                          <p className="text-mist/50">How it was resolved</p>
                          <p>{incident.resolution}</p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="grid gap-6">
                <div className="rounded-[28px] border border-white/10 bg-ink/70 p-5">
                  <h2 className="text-xl font-semibold text-white">Response insights</h2>
                  <div className="mt-5 grid gap-4">
                    {insights.map((insight) => (
                      <article key={insight.title} className="rounded-3xl border border-white/10 bg-white/5 p-4">
                        <p className="text-sm font-semibold text-white">{insight.title}</p>
                        <p className="mt-2 text-sm leading-6 text-mist/75">{insight.detail}</p>
                      </article>
                    ))}
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
                  <h2 className="text-xl font-semibold text-white">Baseline comparison</h2>
                  <p className="mt-1 text-sm text-mist/70">
                    Visual shorthand for current vs expected sensor operating envelope
                  </p>

                  <div className="mt-6 space-y-5">
                    {anomalies.slice(0, 3).map((anomaly) => (
                      <div key={anomaly.id}>
                        <div className="mb-2 flex items-center justify-between text-sm">
                          <span className="text-white">{anomaly.metric}</span>
                          <span className="text-ember">{anomaly.deviation}</span>
                        </div>
                        <div className="relative h-3 overflow-hidden rounded-full bg-white/10">
                          <div className="absolute inset-y-0 left-0 w-1/3 rounded-full bg-surge/60" />
                          <div className="absolute inset-y-0 left-[40%] w-[48%] rounded-full bg-gradient-to-r from-signal to-ember" />
                        </div>
                        <div className="mt-2 flex justify-between text-xs text-mist/50">
                          <span>Expected band</span>
                          <span>Current pressure</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export default App;
