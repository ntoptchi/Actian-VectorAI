export type Severity = "Critical" | "Elevated" | "Watching";

export type Metric = {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down";
};

export type Anomaly = {
  id: string;
  metric: string;
  value: string;
  expected: string;
  deviation: string;
  severity: Severity;
  scope: string;
  signal: string;
};

export type IncidentMatch = {
  id: string;
  incident: string;
  similarity: number;
  cause: string;
  resolution: string;
  impact: string;
  owner: string;
};

export type Insight = {
  title: string;
  detail: string;
};

export const metrics: Metric[] = [
  { label: "Active anomalies", value: "12", change: "+4 vs 1h", trend: "up" },
  { label: "Services affected", value: "5", change: "2 critical", trend: "up" },
  { label: "Matched incidents", value: "28", change: "86% precision", trend: "up" },
  { label: "Median recovery path", value: "42 min", change: "-13 min", trend: "down" },
];

export const anomalies: Anomaly[] = [
  {
    id: "AN-1042",
    metric: "Checkout latency",
    value: "1.84s p95",
    expected: "740ms p95",
    deviation: "+149%",
    severity: "Critical",
    scope: "Payments / us-east",
    signal: "Latency spike started after the 21:10 deployment window.",
  },
  {
    id: "AN-1043",
    metric: "Vector query timeout",
    value: "8.3%",
    expected: "1.1%",
    deviation: "+654%",
    severity: "Critical",
    scope: "Similarity search cluster",
    signal: "Correlates with higher embedding queue depth and CPU saturation.",
  },
  {
    id: "AN-1044",
    metric: "Inventory mismatch rate",
    value: "3.7%",
    expected: "0.9%",
    deviation: "+311%",
    severity: "Elevated",
    scope: "ERP sync / catalog",
    signal: "Mismatch events cluster around late-arriving partner feeds.",
  },
  {
    id: "AN-1045",
    metric: "Failed auth refresh",
    value: "2.1%",
    expected: "0.6%",
    deviation: "+250%",
    severity: "Watching",
    scope: "API gateway",
    signal: "Small but persistent rise across mobile sessions.",
  },
];

export const incidentMatches: IncidentMatch[] = [
  {
    id: "INC-8821",
    incident: "Vector index CPU saturation during promotional traffic",
    similarity: 94,
    cause: "Cache miss rate increased after shard rebalance, pushing embedding lookups to hot nodes.",
    resolution: "Reverted shard balancing policy, warmed index cache, and rate-limited non-critical similarity jobs.",
    impact: "Search timeout rate dropped from 7.8% to 1.4% in 19 minutes.",
    owner: "Search Platform",
  },
  {
    id: "INC-8619",
    incident: "Checkout latency regression after payment rules rollout",
    similarity: 91,
    cause: "New fraud scoring path added two sequential upstream validations in the payment service.",
    resolution: "Disabled the new rule set, switched to async scoring fallback, and replayed affected transactions.",
    impact: "p95 latency returned under 800ms within 26 minutes.",
    owner: "Payments",
  },
  {
    id: "INC-8457",
    incident: "Catalog drift from partner feed backlog",
    similarity: 87,
    cause: "Partner feed retries bypassed deduplication and replayed stale inventory deltas.",
    resolution: "Paused feed ingestion, rebuilt the dedupe cursor, then resumed with watermark validation.",
    impact: "Mismatch rate normalized by the next hourly sync.",
    owner: "Commerce Data",
  },
];

export const insights: Insight[] = [
  {
    title: "Most likely root cause",
    detail:
      "Current signals line up most strongly with two previous incidents tied to rollout-related saturation. Deployment rollback or feature flag isolation should be the first branch of response.",
  },
  {
    title: "Best historical recovery path",
    detail:
      "Teams recovered fastest when they combined rollback with cache warming and selective throttling. Incidents that only scaled infrastructure had slower recovery and higher repeat noise.",
  },
  {
    title: "Next action",
    detail:
      "Validate the 21:10 deployment diff against payment rules and vector shard movement. If both changed, isolate the payment rule flag first, then rebalance index traffic away from the hottest nodes.",
  },
];

export const responseTimeline = [
  "21:10 deploy window opened",
  "21:14 checkout latency broke baseline envelope",
  "21:17 vector timeout anomaly crossed critical threshold",
  "21:21 historical incident match confidence exceeded 90%",
  "21:25 recommended recovery path published to responders",
];
