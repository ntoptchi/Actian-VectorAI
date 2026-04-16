import { AnomalyOverviewChart } from "./components/AnomalyOverviewChart";
import { RigSystemsView } from "./components/RigSystemsView";
import {
  alertSummary,
  anomalies,
  anomalyChart,
  demoRigTopology,
  incidentMatches,
  insights,
  metrics,
  responseTimeline,
  type IncidentMatch,
  type Severity,
} from "./data/dashboardData";

const severityBadgeStyles: Record<Severity, string> = {
  Critical: "border-danger/40 bg-danger/10 text-ember",
  Elevated: "border-warning/35 bg-warning/10 text-warning",
  Watching: "border-surge/35 bg-surge/12 text-surge",
};

const severityAccentStyles: Record<Severity, string> = {
  Critical: "bg-ember",
  Elevated: "bg-signal",
  Watching: "bg-surge",
};

function splitMetricValue(value: string) {
  const [primary, ...rest] = value.split(" ");
  return { primary, secondary: rest.join(" ") };
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-2xl">
      <p className="dashboard-eyebrow">{eyebrow}</p>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-[1.95rem]">
        {title}
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-mist/68">{description}</p>
    </div>
  );
}

function KpiCard({
  label,
  value,
  change,
  trend,
}: {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down";
}) {
  const parts = splitMetricValue(value);

  return (
    <article className="dashboard-card dashboard-card-strong min-h-[118px] p-4">
      <p className="dashboard-meta text-mist/48">{label}</p>
      <div className="mt-5 flex items-end justify-between gap-4">
        <div className="flex items-end gap-1.5">
          <span className="text-[2rem] font-semibold leading-none text-white">{parts.primary}</span>
          {parts.secondary ? (
            <span className="dashboard-meta-soft pb-1 text-mist/58">{parts.secondary}</span>
          ) : null}
        </div>
        <span className={`text-sm font-medium ${trend === "up" ? "text-ember" : "text-surge"}`}>
          {change}
        </span>
      </div>
    </article>
  );
}

function AlertRailCard({
  label,
  value,
  detail,
  severity,
}: {
  label: string;
  value: string;
  detail: string;
  severity: Severity;
}) {
  return (
    <article className="dashboard-card p-4 transition-colors duration-200 hover:border-[rgba(120,160,255,0.18)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="dashboard-meta text-mist/46">{label}</p>
          <p className="mt-2 text-base font-semibold text-white">{value}</p>
        </div>
        <span className={`dashboard-meta rounded-full border px-2.5 py-1 ${severityBadgeStyles[severity]}`}>
          {severity}
        </span>
      </div>
      <p className="mt-3 text-sm leading-5 text-mist/66">{detail}</p>
    </article>
  );
}

function AnomalyCard({
  anomaly,
  index,
}: {
  anomaly: (typeof anomalies)[number];
  index: number;
}) {
  const currentValue = splitMetricValue(anomaly.value);
  const expectedValue = splitMetricValue(anomaly.expected);

  return (
    <article className="dashboard-card group relative overflow-hidden p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-[rgba(120,160,255,0.18)]">
      <div className={`absolute inset-y-0 left-0 w-1 ${severityAccentStyles[anomaly.severity]}`} />
      <div className="flex flex-col gap-4 pl-2 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="dashboard-meta text-mist/42">0{index + 1}</span>
            <h3 className="text-lg font-semibold text-white">{anomaly.metric}</h3>
            <span className={`dashboard-meta rounded-full border px-2.5 py-1 ${severityBadgeStyles[anomaly.severity]}`}>
              {anomaly.severity}
            </span>
          </div>
          <p className="mt-2 text-sm text-mist/58">{anomaly.scope}</p>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-mist/76">{anomaly.signal}</p>
        </div>

        <div className="grid min-w-full gap-3 sm:grid-cols-3 xl:min-w-[360px] xl:max-w-[380px]">
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3">
            <p className="dashboard-meta text-mist/42">Current</p>
            <div className="mt-3 flex items-end gap-1.5">
              <span className="text-xl font-semibold text-white">{currentValue.primary}</span>
              <span className="dashboard-meta-soft pb-0.5 text-mist/52">{currentValue.secondary}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3">
            <p className="dashboard-meta text-mist/42">Expected</p>
            <div className="mt-3 flex items-end gap-1.5">
              <span className="text-xl font-semibold text-white">{expectedValue.primary}</span>
              <span className="dashboard-meta-soft pb-0.5 text-mist/52">{expectedValue.secondary}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3">
            <p className="dashboard-meta text-mist/42">Deviation</p>
            <p className="mt-3 text-xl font-semibold text-ember">{anomaly.deviation}</p>
          </div>
        </div>
      </div>
    </article>
  );
}

function IncidentEvidenceCard({ incident }: { incident: IncidentMatch }) {
  return (
    <article className="dashboard-card group cursor-pointer p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-[rgba(120,160,255,0.18)] hover:bg-[rgba(15,23,38,0.98)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="dashboard-id rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-2.5 py-1 text-mist/62">
              {incident.id}
            </span>
            <span className="dashboard-meta text-mist/40">{incident.owner}</span>
          </div>
          <h3 className="mt-3 text-lg font-semibold text-white">{incident.incident}</h3>
        </div>
        <div className="rounded-2xl border border-signal/28 bg-signal/10 px-4 py-3 text-right">
          <p className="dashboard-meta text-mist/46">Match</p>
          <p className="mt-1 text-2xl font-semibold leading-none text-white">{incident.similarity}%</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] p-4">
          <p className="dashboard-meta text-mist/44">Past issue</p>
          <p className="mt-3 text-sm leading-6 text-mist/74">{incident.cause}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] p-4">
          <p className="dashboard-meta text-mist/44">Resolution</p>
          <p className="mt-3 text-sm leading-6 text-mist/74">{incident.resolution}</p>
        </div>
      </div>
    </article>
  );
}

function InsightCard({
  title,
  detail,
  index,
}: {
  title: string;
  detail: string;
  index: number;
}) {
  return (
    <article className="dashboard-card p-4">
      <div className="flex items-start gap-4">
        <span className="dashboard-meta mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.88)] text-white">
          0{index + 1}
        </span>
        <div>
          <p className="text-sm font-semibold text-white">{title}</p>
          <p className="mt-2 text-sm leading-6 text-mist/74">{detail}</p>
        </div>
      </div>
    </article>
  );
}

function BaselineComparisonCard({ anomaly }: { anomaly: (typeof anomalies)[number] }) {
  const deviationValue = Number.parseInt(anomaly.deviation.replace(/[^\d-]/g, ""), 10);
  const currentRatio = Math.min(92, 38 + deviationValue / 6);
  const expectedStart = Math.max(8, currentRatio - 24);

  return (
    <article className="dashboard-card p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-white">{anomaly.metric}</p>
          <p className="dashboard-meta text-mist/42">{anomaly.scope}</p>
        </div>
        <span className={`dashboard-meta rounded-full border px-2.5 py-1 ${severityBadgeStyles[anomaly.severity]}`}>
          {anomaly.deviation}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <div className="relative h-3 overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
          <div
            className="absolute inset-y-0 rounded-full bg-signal/28"
            style={{ left: `${expectedStart}%`, width: "18%" }}
          />
          <div
            className="absolute inset-y-[1px] w-1.5 -translate-x-1/2 rounded-full bg-mist shadow-[0_0_14px_rgba(59,130,246,0.18)]"
            style={{ left: `${currentRatio}%` }}
          />
        </div>
        <div className="dashboard-meta-soft flex justify-between text-mist/48">
          <span>Expected band</span>
          <span>Current sensor state</span>
        </div>
      </div>
    </article>
  );
}

function App() {
  const primaryIncident = incidentMatches[0];

  return (
    <main className="min-h-screen overflow-hidden text-mist">
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[30px] border border-[rgba(120,160,255,0.1)] bg-[rgba(11,18,32,0.94)] px-4 py-5 shadow-glow sm:px-6 sm:py-6 lg:px-7 lg:py-7">
          <div className="pointer-events-none absolute inset-0 bg-grid bg-[size:42px_42px] opacity-[0.07]" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-signal/6 to-transparent" />
          <div className="pointer-events-none absolute -left-16 top-20 h-52 w-52 rounded-full bg-signal/6 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 right-0 h-60 w-60 rounded-full bg-cyan/4 blur-3xl" />

          <div className="relative z-10 space-y-10">
            <section className="space-y-6">
              <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr] xl:items-end">
                <div className="max-w-3xl">
                  <p className="dashboard-eyebrow">Active sensor intelligence dashboard</p>
                  <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-[3.2rem] sm:leading-[1.02]">
                    Detect anomalies, match prior incidents, and surface the fastest response.
                  </h1>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-mist/72 sm:text-base">
                    Live telemetry vs baseline, linked to resolved field incidents.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {metrics.map((metric) => (
                    <KpiCard key={metric.label} {...metric} />
                  ))}
                </div>
              </div>

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="dashboard-card dashboard-card-strong p-5 sm:p-6">
                  <div className="flex flex-col gap-4 border-b border-white/8 pb-5 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <p className="dashboard-eyebrow">Overview</p>
                      <h2 className="mt-2 text-2xl font-semibold text-white">Anomaly Overview</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-mist/66">
                        Vibration vs expected range for compressor line 3.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.72)] px-3 py-1.5 text-mist/62">
                        Expected band
                      </span>
                      <span className="dashboard-meta-soft rounded-full border border-signal/25 bg-signal/10 px-3 py-1.5 text-signal">
                        Sustained anomaly window
                      </span>
                      <span className="dashboard-meta-soft rounded-full border border-danger/28 bg-danger/10 px-3 py-1.5 text-ember">
                        Critical out-of-band points
                      </span>
                    </div>
                  </div>

                  <div className="mt-5">
                    <AnomalyOverviewChart points={anomalyChart} />
                  </div>
                </div>

                <aside className="grid gap-3">
                  {alertSummary.map((item) => (
                    <AlertRailCard key={item.label} {...item} />
                  ))}
                </aside>
              </div>
            </section>

            <section className="space-y-5">
              <SectionHeading
                eyebrow="Diagnosis"
                title="Abnormal state, affected systems, next response"
                description="Active outliers, affected rig systems, and the best matching response path."
              />

              <div className="space-y-5">
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_360px]">
                  <div className="space-y-4">
                    {anomalies.map((anomaly, index) => (
                      <AnomalyCard key={anomaly.id} anomaly={anomaly} index={index} />
                    ))}
                  </div>

                  <aside className="xl:sticky xl:top-6 xl:self-start">
                    <section className="dashboard-card dashboard-card-strong p-5">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="dashboard-eyebrow">Closest prior incident</p>
                          <h3 className="mt-2 text-xl font-semibold text-white">{primaryIncident.incident}</h3>
                          <p className="mt-2 text-sm text-mist/62">Best historical match for this telemetry pattern</p>
                        </div>
                        <div className="rounded-2xl border border-signal/28 bg-signal/10 px-4 py-3 text-right">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-mist/46">Confidence</p>
                          <p className="mt-1 text-3xl font-semibold leading-none text-white">{primaryIncident.similarity}%</p>
                        </div>
                      </div>

                      <div className="mt-5 space-y-4">
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Cause</p>
                          <p className="mt-3 text-sm leading-6 text-mist/76">{primaryIncident.cause}</p>
                        </div>
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Resolution</p>
                          <p className="mt-3 text-sm leading-6 text-mist/76">{primaryIncident.resolution}</p>
                        </div>
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Outcome</p>
                          <p className="mt-3 text-sm leading-6 text-mist/76">{primaryIncident.impact}</p>
                        </div>
                      </div>
                    </section>
                  </aside>
                </div>

                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,1fr)] xl:items-stretch">
                  <RigSystemsView config={demoRigTopology} />

                  <section className="dashboard-card p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="dashboard-eyebrow">Recommended action sequence</p>
                        <h3 className="mt-2 text-xl font-semibold text-white">Field response sequence</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        5-step playbook
                      </span>
                    </div>

                    <ol className="mt-5 space-y-3">
                      {responseTimeline.map((step, index) => (
                        <li
                          key={step}
                          className="flex gap-3 rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] p-3.5"
                        >
                          <span className="dashboard-meta mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-signal/24 bg-signal/12 text-signal">
                            {index + 1}
                          </span>
                          <span className="text-sm leading-6 text-mist/78">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </section>
                </div>
              </div>
            </section>

            <section className="space-y-5">
              <SectionHeading
                eyebrow="Investigation"
                title="Evidence, guidance, baseline"
                description="Ranked incidents, operator guidance, and baseline evidence."
              />

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_0.95fr]">
                <section className="space-y-4">
                  {incidentMatches.map((incident) => (
                    <IncidentEvidenceCard key={incident.id} incident={incident} />
                  ))}
                </section>

                <section className="grid gap-5">
                  <div className="dashboard-card dashboard-card-strong p-5">
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="dashboard-eyebrow">Response insights</p>
                        <h3 className="mt-2 text-xl font-semibold text-white">Operator guidance</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        Action oriented
                      </span>
                    </div>
                    <div className="mt-5 grid gap-3">
                      {insights.map((insight, index) => (
                        <InsightCard key={insight.title} index={index} {...insight} />
                      ))}
                    </div>
                  </div>

                  <div className="dashboard-card p-5">
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="dashboard-eyebrow">Baseline comparison</p>
                        <h3 className="mt-2 text-xl font-semibold text-white">Current vs expected envelope</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        Evidence
                      </span>
                    </div>
                    <div className="mt-5 grid gap-3">
                      {anomalies.slice(0, 3).map((anomaly) => (
                        <BaselineComparisonCard key={anomaly.id} anomaly={anomaly} />
                      ))}
                    </div>
                  </div>
                </section>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}

export default App;
