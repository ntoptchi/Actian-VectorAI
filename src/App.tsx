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

const railBadgeStyles: Record<Severity, string> = {
  Critical: "border-danger/22 bg-danger/6 text-ember/78",
  Elevated: "border-warning/22 bg-warning/6 text-warning/80",
  Watching: "border-surge/20 bg-surge/8 text-surge/78",
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
      <h2 className="mt-2.5 text-[1.85rem] font-semibold tracking-tight text-white sm:text-[1.9rem]">
        {title}
      </h2>
      <p className="mt-1.5 max-w-xl text-sm leading-6 text-mist/66">{description}</p>
    </div>
  );
}

function KpiCard({
  label,
  value,
  change,
  trend,
  featured = false,
  secondary = false,
  subdued = false,
}: {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down";
  featured?: boolean;
  secondary?: boolean;
  subdued?: boolean;
}) {
  const parts = splitMetricValue(value);

  return (
    <article
      className={`dashboard-card min-h-[108px] transition-colors duration-200 ${
        featured
          ? "border-[rgba(120,160,255,0.14)] bg-[linear-gradient(180deg,rgba(16,24,38,0.98),rgba(11,18,32,0.96))] p-4 shadow-[0_14px_24px_rgba(0,0,0,0.16)]"
          : secondary
            ? "border-[rgba(120,160,255,0.1)] bg-[linear-gradient(180deg,rgba(12,20,34,0.95),rgba(15,23,38,0.89))] p-4 shadow-[0_11px_22px_rgba(0,0,0,0.15)]"
          : subdued
            ? "border-[rgba(120,160,255,0.05)] bg-[linear-gradient(180deg,rgba(11,18,32,0.88),rgba(15,23,38,0.82))] p-4 shadow-[0_6px_14px_rgba(0,0,0,0.12)]"
            : "border-[rgba(120,160,255,0.08)] bg-[linear-gradient(180deg,rgba(11,18,32,0.92),rgba(15,23,38,0.88))] p-4 shadow-[0_8px_18px_rgba(0,0,0,0.14)]"
      }`}
    >
      <div className="flex h-full min-h-[72px] flex-col">
        <p className={`dashboard-meta ${featured ? "text-cyan/80" : secondary ? "text-mist/64" : subdued ? "text-mist/38" : "text-mist/54"}`}>{label}</p>
        <div className="mt-auto flex items-end justify-between gap-4 pt-4">
          <div className="min-w-0">
            <div className="flex items-end gap-1.5">
              <span className={`${featured ? "text-[2.12rem]" : secondary ? "text-[2.08rem]" : "text-[2rem]"} font-semibold leading-none ${subdued ? "text-mist/86" : "text-white"}`}>
                {parts.primary}
              </span>
              {parts.secondary ? (
                <span className={`dashboard-meta-soft pb-1 ${subdued ? "text-mist/48" : "text-mist/58"}`}>{parts.secondary}</span>
              ) : null}
            </div>
          </div>
          <span
            className={`self-end text-sm font-medium ${trend === "up" ? "text-ember" : "text-surge"} ${subdued ? "opacity-72" : ""}`}
          >
            {change}
          </span>
        </div>
      </div>
    </article>
  );
}

function AlertRailCard({
  label,
  value,
  detail,
  severity,
  featured = false,
}: {
  label: string;
  value: string;
  detail: string;
  severity: Severity;
  featured?: boolean;
}) {
  return (
    <article
      className={`dashboard-card transition-colors duration-200 hover:border-[rgba(120,160,255,0.18)] ${
        featured
          ? "min-h-[132px] border-[rgba(245,158,11,0.18)] bg-[linear-gradient(180deg,rgba(22,28,40,0.985),rgba(11,18,32,0.96))] p-4 shadow-[0_14px_24px_rgba(0,0,0,0.18)]"
          : "min-h-[132px] border-[rgba(120,160,255,0.06)] bg-[linear-gradient(180deg,rgba(11,18,32,0.9),rgba(15,23,38,0.84))] p-4 shadow-[0_8px_18px_rgba(0,0,0,0.13)]"
      }`}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className={`dashboard-meta ${featured ? "text-warning/74" : "text-mist/44"}`}>{label}</p>
          </div>
          <span
            className={`dashboard-meta shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] tracking-[0.04em] ${railBadgeStyles[severity]}`}
          >
            {severity}
          </span>
        </div>
        <div className="mt-3">
          <p className={`font-semibold text-white ${featured ? "text-[1.35rem] leading-none" : "text-base"}`}>{value}</p>
        </div>
        <p
          className={`min-w-0 text-sm text-mist/64 ${featured ? "mt-2.5 leading-5" : "mt-2.5 leading-5"}`}
          style={{
            whiteSpace: "normal",
            overflow: "hidden",
            textOverflow: "ellipsis",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflowWrap: "break-word",
          }}
        >
          {detail}
        </p>
      </div>
    </article>
  );
}

function StatusBanner({
  severity,
  asset,
  statusTokens,
}: {
  severity: string;
  asset: string;
  statusTokens: [string, string, string];
}) {
  return (
    <div className="dashboard-card dashboard-card-strong p-2.5">
      <div className="flex flex-col gap-2 md:grid md:grid-cols-[minmax(272px,auto)_minmax(0,1fr)] md:items-center md:gap-2.5">
        <div className="flex flex-wrap items-center gap-2 md:min-w-[286px]">
          <span className="dashboard-meta rounded-full border border-danger/35 bg-danger/10 px-2.5 py-0.5 text-ember">
            {severity}
          </span>
          <span className="dashboard-meta rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.72)] px-2.5 py-0.5 text-mist/62">
            {asset}
          </span>
        </div>
        <div className="grid gap-0.5 md:max-w-[22rem] md:justify-self-start">
          {statusTokens.map((token) => (
            <div
              key={token}
              className="flex items-center gap-2"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-mist/34" />
              <span className="dashboard-meta-soft text-mist/68">{token}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
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
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="dashboard-meta text-mist/42">0{index + 1}</span>
            <h3 className="text-lg font-semibold text-white">{anomaly.metric}</h3>
            <span className={`dashboard-meta rounded-full border px-2.5 py-1 ${severityBadgeStyles[anomaly.severity]}`}>
              {anomaly.severity}
            </span>
          </div>
          <p className="mt-1.5 text-sm text-mist/58">{anomaly.scope}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-mist/76">{anomaly.signal}</p>
        </div>

        <div className="grid min-w-full gap-3 sm:grid-cols-3 xl:min-w-[372px] xl:max-w-[396px]">
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3.5">
            <p className="dashboard-meta text-mist/42">Current</p>
            <div className="mt-2.5 flex items-end gap-1.5">
              <span className="text-xl font-semibold text-white">{currentValue.primary}</span>
              <span className="dashboard-meta-soft pb-0.5 text-mist/52">{currentValue.secondary}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3.5">
            <p className="dashboard-meta text-mist/42">Expected</p>
            <div className="mt-2.5 flex items-end gap-1.5">
              <span className="text-xl font-semibold text-white">{expectedValue.primary}</span>
              <span className="dashboard-meta-soft pb-0.5 text-mist/52">{expectedValue.secondary}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.74)] px-4 py-3.5">
            <p className="dashboard-meta text-mist/42">Deviation</p>
            <p className="mt-2.5 text-xl font-semibold text-ember">{anomaly.deviation}</p>
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

      <div className="mt-4.5 grid gap-4 lg:grid-cols-2">
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
          <p className="mt-1.5 max-w-[34ch] text-sm leading-6 text-mist/74">{detail}</p>
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

      <div className="mt-3.5 space-y-2.5">
        <div className="relative h-3 overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
          <div
            className="absolute inset-y-0 rounded-full bg-signal/28"
            style={{ left: `${expectedStart}%`, width: "18%" }}
          />
          <div
            className="absolute inset-y-[0.5px] w-2 -translate-x-1/2 rounded-full bg-mist shadow-[0_0_16px_rgba(59,130,246,0.22)]"
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

          <div className="relative z-10 space-y-9">
            <section className="space-y-3.5">
              <StatusBanner
                severity="Critical excursion active"
                asset="Compressor line 3 / north wing"
                statusTokens={[
                  "Above tolerance since 21:10",
                  "High prior-event correlation",
                  "Workflow open",
                ]}
              />

              <div className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr] xl:items-end">
                <div className="max-w-[34rem]">
                  <h1 className="max-w-[12ch] text-[2.12rem] font-bold tracking-tight text-white sm:text-[2.3rem] sm:leading-[1.03]">
                    <span className="block whitespace-nowrap">Excursion status</span>
                  </h1>
                  <div className="mt-0.5 max-w-[33rem] space-y-0 text-sm leading-5.5 text-mist/82 sm:text-[0.95rem]">
                    <p>Compressor L3 remains in sustained breach with elevated thermal load.</p>
                    <p>Maintain reduced load and inspection readiness until the trace stabilizes.</p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  {metrics.map((metric) => (
                    <KpiCard
                      key={metric.label}
                      {...metric}
                      featured={metric.label === "Systems affected"}
                      secondary={metric.label === "Median restore path"}
                      subdued={metric.label === "Prior events linked"}
                    />
                  ))}
                </div>
              </div>

              <div className="grid gap-5 pt-0.5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="dashboard-card dashboard-card-strong border-[rgba(120,160,255,0.2)] bg-[linear-gradient(180deg,rgba(16,24,40,0.995),rgba(11,18,32,0.98))] p-5 shadow-[0_24px_46px_rgba(0,0,0,0.28)] sm:p-6">
                  <div className="flex flex-col gap-2.5 border-b border-white/8 pb-4 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h2 className="text-[1.28rem] font-medium text-white/68">Excursion Trace</h2>
                      <p className="mt-1 max-w-2xl text-sm leading-5.5 text-mist/64">
                        Compressor line 3 vibration against operating tolerance.
                      </p>
                    </div>
                    <div className="flex items-center gap-4 text-[12px] sm:max-w-[24rem] sm:justify-end">
                      <span className="dashboard-meta-soft inline-flex items-center gap-1.5 whitespace-nowrap text-mist/60">
                        <span className="h-1.5 w-3 rounded-full bg-[rgba(59,130,246,0.46)]" />
                        Tolerance band
                      </span>
                      <span className="dashboard-meta-soft inline-flex items-center gap-1.5 whitespace-nowrap text-cyan/84">
                        <span className="h-1.5 w-3 rounded-full bg-cyan/70" />
                        Sustained excursion
                      </span>
                      <span className="dashboard-meta-soft inline-flex items-center gap-1.5 whitespace-nowrap text-ember/84">
                        <span className="h-1.5 w-1.5 rounded-full bg-danger/85" />
                        Breach points
                      </span>
                    </div>
                  </div>

                  <div className="mt-4.5">
                    <AnomalyOverviewChart points={anomalyChart} />
                  </div>
                </div>

                <aside className="grid gap-3">
                  {alertSummary.map((item) => (
                    <AlertRailCard key={item.label} {...item} featured={item.label === "Critical window"} />
                  ))}
                </aside>
              </div>
            </section>

            <section className="space-y-4.5">
              <SectionHeading
                eyebrow="Diagnosis"
                title="Detected excursion, affected systems, next response"
                description="Active deviations, affected rig systems, and the closest response path."
              />

              <div className="space-y-4.5">
                <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_360px]">
                  <div className="space-y-3.5">
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
                          <p className="mt-1.5 text-sm text-mist/60">Closest prior event for this telemetry pattern</p>
                        </div>
                        <div className="rounded-2xl border border-signal/28 bg-signal/10 px-4 py-3 text-right">
                          <p className="text-[11px] uppercase tracking-[0.18em] text-mist/46">Correlation</p>
                          <p className="mt-1 text-3xl font-semibold leading-none text-white">{primaryIncident.similarity}%</p>
                        </div>
                      </div>

                      <div className="mt-4.5 space-y-3">
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Cause</p>
                          <p className="mt-2.5 text-sm leading-6 text-mist/74">{primaryIncident.cause}</p>
                        </div>
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Resolution</p>
                          <p className="mt-2.5 text-sm leading-6 text-mist/74">{primaryIncident.resolution}</p>
                        </div>
                        <div className="rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.78)] p-4">
                          <p className="dashboard-meta text-mist/42">Outcome</p>
                          <p className="mt-2.5 text-sm leading-6 text-mist/74">{primaryIncident.impact}</p>
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
                        <h3 className="mt-2 text-xl font-semibold text-white">Response workflow</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        5-step sequence
                      </span>
                    </div>

                    <ol className="mt-4.5 space-y-2.5">
                      {responseTimeline.map((step, index) => (
                        <li
                          key={step}
                          className="flex gap-3 rounded-2xl border border-[rgba(120,160,255,0.08)] bg-[rgba(15,23,38,0.72)] px-3.5 py-3"
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

            <section className="space-y-4.5">
              <SectionHeading
                eyebrow="Investigation"
                title="Event evidence, actions, baseline"
                description="Ranked prior events, corrective actions, and tolerance evidence."
              />

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_0.95fr]">
                <section className="space-y-3.5">
                  {incidentMatches.map((incident) => (
                    <IncidentEvidenceCard key={incident.id} incident={incident} />
                  ))}
                </section>

                <section className="grid gap-4.5">
                  <div className="dashboard-card dashboard-card-strong p-5">
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="dashboard-eyebrow">Response insights</p>
                        <h3 className="mt-2 text-xl font-semibold text-white">Corrective actions</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        Response ready
                      </span>
                    </div>
                    <div className="mt-4.5 grid gap-3">
                      {insights.map((insight, index) => (
                        <InsightCard key={insight.title} index={index} {...insight} />
                      ))}
                    </div>
                  </div>

                  <div className="dashboard-card p-5">
                    <div className="flex items-end justify-between gap-4">
                      <div>
                        <p className="dashboard-eyebrow">Baseline comparison</p>
                        <h3 className="mt-2 text-xl font-semibold text-white">Current vs tolerance envelope</h3>
                      </div>
                      <span className="dashboard-meta-soft rounded-full border border-[rgba(120,160,255,0.12)] bg-[rgba(15,23,38,0.74)] px-3 py-1.5 text-mist/52">
                        Evidence
                      </span>
                    </div>
                    <div className="mt-4.5 grid gap-3">
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
