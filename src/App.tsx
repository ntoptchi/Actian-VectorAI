import { useEffect, useRef, useState } from "react";
import { AnomalyOverviewChart } from "./components/AnomalyOverviewChart";
import { RigSystemsView } from "./components/RigSystemsView";
import {
  defaultAlertSummary,
  defaultAnomalies,
  defaultAnomalyChart,
  defaultIncidentMatches,
  defaultInsights,
  defaultMetrics,
  defaultResponseTimeline,
  defaultRigTopology,
  type Anomaly,
  type IncidentMatch,
  type Severity,
} from "./data/dashboardData";
import { useLiveDashboard } from "./hooks/useLiveDashboard";

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
          ? "border-[rgba(120,160,255,0.18)] bg-[linear-gradient(180deg,rgba(18,28,44,0.995),rgba(11,18,32,0.975))] p-4 shadow-[0_16px_28px_rgba(0,0,0,0.18)]"
          : secondary
            ? "border-[rgba(120,160,255,0.1)] bg-[linear-gradient(180deg,rgba(12,20,34,0.95),rgba(15,23,38,0.89))] p-4 shadow-[0_10px_20px_rgba(0,0,0,0.14)]"
          : subdued
            ? "border-[rgba(120,160,255,0.03)] bg-[linear-gradient(180deg,rgba(10,16,28,0.78),rgba(14,20,32,0.74))] p-4 shadow-[0_3px_8px_rgba(0,0,0,0.08)]"
            : "border-[rgba(120,160,255,0.08)] bg-[linear-gradient(180deg,rgba(11,18,32,0.92),rgba(15,23,38,0.88))] p-4 shadow-[0_8px_18px_rgba(0,0,0,0.14)]"
      }`}
    >
      <div className="flex h-full min-h-[72px] flex-col">
        <p className={`dashboard-meta ${featured ? "text-cyan/88" : secondary ? "text-mist/72" : subdued ? "text-mist/34" : "text-mist/58"}`}>{label}</p>
        <div className="mt-auto flex items-end justify-between gap-4 pt-4">
          <div className="min-w-0">
            <div className="flex items-end gap-1.5">
              <span className={`${featured ? "text-[2.18rem]" : secondary ? "text-[2.06rem]" : subdued ? "text-[1.82rem]" : "text-[1.98rem]"} font-semibold leading-none ${subdued ? "text-mist/72" : featured ? "text-white" : "text-white/96"}`}>
                {parts.primary}
              </span>
              {parts.secondary ? (
                <span className={`dashboard-meta-soft pb-1 ${featured ? "text-mist/64" : subdued ? "text-mist/38" : "text-mist/56"}`}>{parts.secondary}</span>
              ) : null}
            </div>
          </div>
          <span
            className={`self-end text-sm font-medium ${trend === "up" ? "text-ember" : "text-surge"} ${featured ? "" : subdued ? "opacity-45" : "opacity-80"}`}
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
      className={`transition-colors duration-200 ${
        featured
          ? "min-h-[132px] border-[rgba(245,158,11,0.18)] bg-[linear-gradient(180deg,rgba(22,28,40,0.985),rgba(11,18,32,0.96))] p-4 shadow-[0_14px_24px_rgba(0,0,0,0.18)]"
          : "rounded-[16px] border border-[rgba(120,160,255,0.025)] bg-[rgba(15,23,38,0.28)] px-3 py-1.5 shadow-[0_1px_4px_rgba(0,0,0,0.05)]"
      }`}
    >
      <div className="flex h-full flex-col">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className={`dashboard-meta ${featured ? "text-warning/74" : "text-mist/44"}`}>{label}</p>
          </div>
          <span
            className={`dashboard-meta shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] tracking-[0.02em] ${featured ? railBadgeStyles[severity] : "border-white/6 bg-white/[0.03] text-mist/46"}`}
          >
            {severity}
          </span>
        </div>
        <div className={featured ? "mt-3" : "mt-1.5"}>
          <p className={`font-semibold text-white ${featured ? "text-[1.35rem] leading-none" : "text-[0.98rem] leading-tight"}`}>{value}</p>
        </div>
        <p
          className={`min-w-0 text-sm text-mist/64 ${featured ? "mt-2.5 leading-5" : "mt-0.5 leading-[1.15rem] text-mist/56"}`}
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
    <div className="dashboard-card dashboard-card-strong p-1">
      <div className="flex flex-col gap-1 md:grid md:grid-cols-[minmax(272px,auto)_minmax(0,1fr)] md:items-center md:gap-1">
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
  isFresh,
}: {
  anomaly: Anomaly;
  index: number;
  isFresh?: boolean;
}) {
  const currentValue = splitMetricValue(anomaly.value);
  const expectedValue = splitMetricValue(anomaly.expected);

  return (
    <article
      className={`dashboard-card group relative overflow-hidden p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-[rgba(120,160,255,0.18)] ${
        isFresh ? "animate-pulse ring-1 ring-signal/40" : ""
      }`}
    >
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

function BaselineComparisonCard({ anomaly }: { anomaly: Anomaly }) {
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
  const { state, isLive, lastUpdated } = useLiveDashboard();

  const metrics = state?.metrics ?? defaultMetrics;
  const alertSummary = state?.alertSummary ?? defaultAlertSummary;
  const anomalies = state?.anomalies?.length ? state.anomalies : defaultAnomalies;
  const incidentMatches = state?.incidentMatches?.length
    ? state.incidentMatches
    : defaultIncidentMatches;
  const insights = state?.insights?.length ? state.insights : defaultInsights;
  const anomalyChart = state?.anomalyChart?.length
    ? state.anomalyChart
    : defaultAnomalyChart;
  const responseTimeline = state?.responseTimeline?.length
    ? state.responseTimeline
    : defaultResponseTimeline;
  const rigTopology = state?.rigTopology ?? defaultRigTopology;

  // Flash newly-arrived anomalies for 2s.
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set());
  const prevIds = useRef<Set<string>>(new Set(defaultAnomalies.map((a) => a.id)));
  useEffect(() => {
    const current = new Set(anomalies.map((a) => a.id));
    const incoming = [...current].filter((id) => !prevIds.current.has(id));
    if (incoming.length > 0) {
      setFreshIds((prev) => new Set([...prev, ...incoming]));
      window.setTimeout(() => {
        setFreshIds((prev) => {
          const next = new Set(prev);
          incoming.forEach((id) => next.delete(id));
          return next;
        });
      }, 2000);
    }
    prevIds.current = current;
  }, [anomalies]);

  const primaryIncident = incidentMatches[0] ?? defaultIncidentMatches[0];
  const orderedMetrics = [
    metrics.find((metric) => metric.label === "Systems affected"),
    metrics.find((metric) => metric.label === "Median restore path"),
    metrics.find((metric) => metric.label === "Active excursions"),
    metrics.find((metric) => metric.label === "Prior events linked"),
  ].filter(Boolean) as typeof metrics;
  const orderedAlertSummary = [
    ...alertSummary.filter((item) => item.label === "Critical window"),
    ...alertSummary.filter((item) => item.label === "Affected asset"),
    ...alertSummary.filter((item) => item.label === "Top driver"),
    ...alertSummary.filter(
      (item) =>
        item.label !== "Critical window" &&
        item.label !== "Affected asset" &&
        item.label !== "Top driver",
    ),
  ];

  return (
    <main className="min-h-screen overflow-hidden text-mist">
      <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[30px] border border-[rgba(120,160,255,0.1)] bg-[rgba(11,18,32,0.94)] px-4 py-4.5 shadow-glow sm:px-6 sm:py-5.5 lg:px-7 lg:py-6">
          <div className="pointer-events-none absolute inset-0 bg-grid bg-[size:42px_42px] opacity-[0.07]" />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-signal/6 to-transparent" />
          <div className="pointer-events-none absolute -left-16 top-20 h-52 w-52 rounded-full bg-signal/6 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 right-0 h-60 w-60 rounded-full bg-cyan/4 blur-3xl" />

          <div className="relative z-10 space-y-9">
            <section className="space-y-3.5">
              <div className="flex items-center justify-end gap-2 text-[11px] uppercase tracking-[0.18em]">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    isLive ? "bg-surge animate-pulse" : "bg-mist/30"
                  }`}
                />
                <span className={isLive ? "text-surge/80" : "text-mist/40"}>
                  {isLive ? "Live" : "Offline · fallback data"}
                </span>
                {lastUpdated ? (
                  <span className="text-mist/40">
                    · {lastUpdated.toLocaleTimeString()}
                  </span>
                ) : null}
              </div>
              <StatusBanner
                severity="Critical excursion active"
                asset="Compressor line 3 / north wing"
                statusTokens={[
                  "Above tolerance since 21:10",
                  "High prior-event correlation",
                  "Workflow open",
                ]}
              />

              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    {orderedMetrics.map((metric) => (
                      <KpiCard
                        key={metric.label}
                        {...metric}
                        featured={metric.label === "Systems affected"}
                        secondary={metric.label === "Median restore path"}
                        subdued={metric.label === "Prior events linked"}
                      />
                    ))}
                  </div>

                  <div className="max-w-[34rem]">
                    <h1 className="max-w-[12ch] text-[2.12rem] font-bold tracking-tight text-white sm:text-[2.3rem] sm:leading-[1.03]">
                      <span className="block whitespace-nowrap">Excursion status</span>
                    </h1>
                    <div className="mt-0.5 max-w-[33rem] space-y-0 text-sm leading-5.5 text-mist/82 sm:text-[0.95rem]">
                      <p>Compressor L3 remains in sustained breach with elevated thermal load.</p>
                      <p>Maintain reduced load and inspection readiness until the trace stabilizes.</p>
                    </div>
                  </div>

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
                </div>

                <aside className="grid gap-2.5">
                  {orderedAlertSummary.map((item) => (
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
                      <AnomalyCard
                        key={anomaly.id}
                        anomaly={anomaly}
                        index={index}
                        isFresh={freshIds.has(anomaly.id)}
                      />
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
                  <RigSystemsView config={rigTopology} />

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
