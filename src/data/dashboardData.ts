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
    metric: "Vibration amplitude",
    value: "18.4 mm/s",
    expected: "7.1 mm/s",
    deviation: "+149%",
    severity: "Critical",
    scope: "Compressor line 3 / north wing",
    signal: "Amplitude spike started immediately after the 21:10 load transition and stayed above the learned envelope.",
  },
  {
    id: "AN-1043",
    metric: "Bearing temperature",
    value: "83.0 C",
    expected: "61.1 C",
    deviation: "+654%",
    severity: "Critical",
    scope: "Turbine assembly / sensor bank B",
    signal: "Temperature rise correlates with abnormal vibration harmonics and a drop in lubricant pressure.",
  },
  {
    id: "AN-1044",
    metric: "Pressure fluctuation",
    value: "3.7 bar variance",
    expected: "0.9 bar variance",
    deviation: "+311%",
    severity: "Elevated",
    scope: "Cooling loop / sector 4",
    signal: "Variance increase clusters around valve cycling events and delayed flow stabilization.",
  },
  {
    id: "AN-1045",
    metric: "Humidity drift",
    value: "2.1% RH/min",
    expected: "0.6% RH/min",
    deviation: "+250%",
    severity: "Watching",
    scope: "Storage chamber 2",
    signal: "Small but persistent humidity rise across two adjacent environmental sensors.",
  },
];

export const incidentMatches: IncidentMatch[] = [
  {
    id: "INC-8821",
    incident: "Compressor resonance spike during high-load transition",
    similarity: 94,
    cause: "Rotor imbalance intensified during a step-up in load, creating resonance that drove vibration beyond safe limits.",
    resolution: "Reduced line load, rebalanced the rotor assembly, and recalibrated the vibration threshold profile.",
    impact: "Vibration amplitude fell back inside tolerance in 19 minutes.",
    owner: "Reliability Engineering",
  },
  {
    id: "INC-8619",
    incident: "Bearing overheat after lubricant flow restriction",
    similarity: 91,
    cause: "A partially obstructed lubricant line reduced flow to the bearing housing during sustained operation.",
    resolution: "Switched the unit to reduced RPM, cleared the restriction, and flushed the lubrication circuit.",
    impact: "Bearing temperature returned to normal operating range within 26 minutes.",
    owner: "Mechanical Ops",
  },
  {
    id: "INC-8457",
    incident: "Cooling loop instability from valve oscillation",
    similarity: 87,
    cause: "Control valve oscillation caused repeated over-correction, producing pressure swings across the loop.",
    resolution: "Locked the valve to manual mode, damped the control band, and re-tuned the actuator response.",
    impact: "Pressure variance normalized by the next monitoring cycle.",
    owner: "Process Control",
  },
];

export const insights: Insight[] = [
  {
    title: "Most likely root cause",
    detail:
      "Current signals line up most strongly with prior equipment-stress incidents tied to load transitions and restricted flow. Load reduction and mechanical inspection should be the first branch of response.",
  },
  {
    title: "Best historical recovery path",
    detail:
      "Teams recovered fastest when they combined immediate load reduction with targeted mechanical correction. Incidents that only muted alarms without inspecting the asset had slower recovery and higher repeat noise.",
  },
  {
    title: "Next action",
    detail:
      "Validate the 21:10 load transition against compressor vibration, lubricant pressure, and valve-cycling telemetry. If all three moved together, reduce line load first, then inspect the bearing assembly and control valve response.",
  },
];

export const responseTimeline = [
  "21:10 load transition started",
  "21:14 vibration amplitude broke baseline envelope",
  "21:17 bearing temperature anomaly crossed critical threshold",
  "21:21 historical incident match confidence exceeded 90%",
  "21:25 recommended field response published to operators",
];
