export type Severity = "Critical" | "Elevated" | "Watching";

export type Metric = {
  label: string;
  value: string;
  change: string;
  trend: "up" | "down";
};

export type AlertSummary = {
  label: string;
  value: string;
  detail: string;
  severity: Severity;
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

export type ChartPoint = {
  timestamp: string;
  actual: number;
  expectedMin: number;
  expectedMax: number;
  severity: Severity;
};

export type AssetStatus = "normal" | "watch" | "warning" | "critical" | "offline";

export type AssetNode = {
  id: string;
  label: string;
  shortLabel?: string;
  type: string;
  zoneId: string;
  x: number;
  y: number;
  status: AssetStatus;
  anomalyScore?: number;
  metricValue?: string;
  lastUpdated?: string;
};

export type Zone = {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  description?: string;
};

export type TopologyLink = {
  id: string;
  fromAssetId: string;
  toAssetId: string;
};

export type RigTopologyConfig = {
  rigId: string;
  rigName: string;
  viewLabel?: string;
  zones: Zone[];
  assets: AssetNode[];
  links?: TopologyLink[];
};

export const metrics: Metric[] = [
  { label: "Active anomalies", value: "12", change: "+4 vs 1h", trend: "up" },
  { label: "Services affected", value: "5", change: "2 critical", trend: "up" },
  { label: "Matched incidents", value: "28", change: "86% precision", trend: "up" },
  { label: "Median recovery path", value: "42 min", change: "-13 min", trend: "down" },
];

export const alertSummary: AlertSummary[] = [
  {
    label: "Critical window",
    value: "14 min",
    detail: "Sustained out-of-band vibration",
    severity: "Critical",
  },
  {
    label: "Affected asset",
    value: "Compressor L3",
    detail: "North wing lane",
    severity: "Elevated",
  },
  {
    label: "Top driver",
    value: "Load transition",
    detail: "Started 21:10 local",
    severity: "Watching",
  },
  {
    label: "Match confidence",
    value: "94%",
    detail: "Top prior incident",
    severity: "Elevated",
  },
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
    signal: "Spike began after the 21:10 load transition and stayed out of band.",
  },
  {
    id: "AN-1043",
    metric: "Bearing temperature",
    value: "83.0 C",
    expected: "61.1 C",
    deviation: "+654%",
    severity: "Critical",
    scope: "Turbine assembly / sensor bank B",
    signal: "Rise tracks abnormal vibration harmonics and lower lubricant pressure.",
  },
  {
    id: "AN-1044",
    metric: "Pressure fluctuation",
    value: "3.7 bar variance",
    expected: "0.9 bar variance",
    deviation: "+311%",
    severity: "Elevated",
    scope: "Cooling loop / sector 4",
    signal: "Variance rose with valve cycling and slower flow stabilization.",
  },
  {
    id: "AN-1045",
    metric: "Humidity drift",
    value: "2.1% RH/min",
    expected: "0.6% RH/min",
    deviation: "+250%",
    severity: "Watching",
    scope: "Storage chamber 2",
    signal: "Persistent rise across two adjacent environmental sensors.",
  },
];

export const incidentMatches: IncidentMatch[] = [
  {
    id: "INC-8821",
    incident: "Compressor resonance spike during high-load transition",
    similarity: 94,
    cause: "Rotor imbalance intensified during load step-up and drove resonance past safe limits.",
    resolution: "Reduced load, rebalanced the rotor, and recalibrated vibration thresholds.",
    impact: "Vibration returned to tolerance in 19 minutes.",
    owner: "Reliability Engineering",
  },
  {
    id: "INC-8619",
    incident: "Bearing overheat after lubricant flow restriction",
    similarity: 91,
    cause: "A partial lubricant restriction reduced flow to the bearing housing.",
    resolution: "Dropped RPM, cleared the restriction, and flushed the circuit.",
    impact: "Bearing temperature normalized in 26 minutes.",
    owner: "Mechanical Ops",
  },
  {
    id: "INC-8457",
    incident: "Cooling loop instability from valve oscillation",
    similarity: 87,
    cause: "Valve oscillation caused repeated over-correction and loop pressure swings.",
    resolution: "Locked manual mode, damped the control band, and retuned the actuator.",
    impact: "Pressure variance normalized by the next monitoring cycle.",
    owner: "Process Control",
  },
];

export const insights: Insight[] = [
  {
    title: "Most likely root cause",
    detail:
      "Signals align with prior load-transition and restricted-flow incidents. Reduce load and inspect mechanically first.",
  },
  {
    title: "Best historical recovery path",
    detail:
      "Fastest recoveries combined immediate load reduction with targeted mechanical correction. Alarm suppression alone led to slower recovery and more repeat noise.",
  },
  {
    title: "Next action",
    detail:
      "Check the 21:10 load transition against vibration, lubricant pressure, and valve cycling. If all three moved together, cut line load first, then inspect the bearing assembly and control valve.",
  },
];

export const responseTimeline = [
  "21:10 load transition started",
  "21:14 vibration broke baseline",
  "21:17 bearing temperature crossed critical",
  "21:21 match confidence passed 90%",
  "21:25 field response issued",
];

export const anomalyChart: ChartPoint[] = [
  { timestamp: "20:52", actual: 6.5, expectedMin: 5.6, expectedMax: 8.4, severity: "Watching" },
  { timestamp: "20:56", actual: 6.8, expectedMin: 5.7, expectedMax: 8.5, severity: "Watching" },
  { timestamp: "21:00", actual: 7.2, expectedMin: 5.9, expectedMax: 8.7, severity: "Watching" },
  { timestamp: "21:04", actual: 7.6, expectedMin: 6.0, expectedMax: 8.8, severity: "Watching" },
  { timestamp: "21:08", actual: 8.1, expectedMin: 6.1, expectedMax: 9.0, severity: "Watching" },
  { timestamp: "21:12", actual: 10.8, expectedMin: 6.0, expectedMax: 9.1, severity: "Elevated" },
  { timestamp: "21:16", actual: 12.6, expectedMin: 5.9, expectedMax: 9.1, severity: "Elevated" },
  { timestamp: "21:20", actual: 15.2, expectedMin: 5.8, expectedMax: 9.0, severity: "Critical" },
  { timestamp: "21:24", actual: 17.8, expectedMin: 5.7, expectedMax: 8.9, severity: "Critical" },
  { timestamp: "21:28", actual: 18.4, expectedMin: 5.8, expectedMax: 8.9, severity: "Critical" },
  { timestamp: "21:32", actual: 16.7, expectedMin: 5.9, expectedMax: 9.0, severity: "Critical" },
  { timestamp: "21:36", actual: 14.3, expectedMin: 6.0, expectedMax: 9.1, severity: "Elevated" },
  { timestamp: "21:40", actual: 11.8, expectedMin: 6.1, expectedMax: 9.2, severity: "Elevated" },
  { timestamp: "21:44", actual: 9.6, expectedMin: 6.2, expectedMax: 9.2, severity: "Watching" },
  { timestamp: "21:48", actual: 8.8, expectedMin: 6.3, expectedMax: 9.3, severity: "Watching" },
];

export const demoRigTopology: RigTopologyConfig = {
  rigId: "rig-north-atlas-07",
  rigName: "North Atlas 07",
  viewLabel: "Operational schematic by zone",
  zones: [
    {
      id: "compression",
      label: "Compression",
      x: 6,
      y: 10,
      width: 34,
      height: 34,
      description: "Compression and rotating equipment",
    },
    {
      id: "cooling",
      label: "Cooling",
      x: 44,
      y: 10,
      width: 22,
      height: 34,
      description: "Heat exchange and loop control",
    },
    {
      id: "power",
      label: "Power",
      x: 69,
      y: 10,
      width: 25,
      height: 34,
      description: "Generation and distribution",
    },
    {
      id: "safety",
      label: "Safety",
      x: 6,
      y: 50,
      width: 30,
      height: 30,
      description: "Gas detection and response",
    },
    {
      id: "storage",
      label: "Storage",
      x: 40,
      y: 50,
      width: 25,
      height: 30,
      description: "Buffer tanks and containment",
    },
    {
      id: "drilling",
      label: "Drilling",
      x: 69,
      y: 50,
      width: 25,
      height: 30,
      description: "Mud handling and drill-floor systems",
    },
  ],
  assets: [
    {
      id: "compressor-03",
      label: "Compressor-03",
      shortLabel: "C-03",
      type: "Compressor",
      zoneId: "compression",
      x: 18,
      y: 21,
      status: "critical",
      anomalyScore: 98,
      metricValue: "18.4 mm/s vibration",
      lastUpdated: "21:28",
    },
    {
      id: "valve-12",
      label: "Valve-12",
      shortLabel: "V-12",
      type: "Control valve",
      zoneId: "compression",
      x: 31,
      y: 32,
      status: "warning",
      anomalyScore: 74,
      metricValue: "3.7 bar variance",
      lastUpdated: "21:22",
    },
    {
      id: "pump-07",
      label: "Pump-07",
      shortLabel: "P-07",
      type: "Cooling pump",
      zoneId: "cooling",
      x: 51,
      y: 24,
      status: "warning",
      anomalyScore: 68,
      metricValue: "Flow instability",
      lastUpdated: "21:24",
    },
    {
      id: "heat-exchanger-2",
      label: "Heat Exchanger-2",
      shortLabel: "HX-2",
      type: "Heat exchanger",
      zoneId: "cooling",
      x: 59,
      y: 34,
      status: "watch",
      anomalyScore: 42,
      metricValue: "61.8 C outlet",
      lastUpdated: "21:19",
    },
    {
      id: "generator-02",
      label: "Generator-02",
      shortLabel: "G-02",
      type: "Generator",
      zoneId: "power",
      x: 78,
      y: 22,
      status: "normal",
      anomalyScore: 9,
      metricValue: "Load stable",
      lastUpdated: "21:26",
    },
    {
      id: "switchgear-01",
      label: "Switchgear-01",
      shortLabel: "SG-1",
      type: "Switchgear",
      zoneId: "power",
      x: 87,
      y: 33,
      status: "offline",
      anomalyScore: 0,
      metricValue: "Maintenance isolation",
      lastUpdated: "20:58",
    },
    {
      id: "gas-sensor-a",
      label: "Gas Sensor-A",
      shortLabel: "GS-A",
      type: "Gas sensor",
      zoneId: "safety",
      x: 16,
      y: 63,
      status: "watch",
      anomalyScore: 36,
      metricValue: "2.1% drift",
      lastUpdated: "21:17",
    },
    {
      id: "fire-suppression-1",
      label: "Fire Suppression-1",
      shortLabel: "FS-1",
      type: "Safety system",
      zoneId: "safety",
      x: 27,
      y: 72,
      status: "normal",
      anomalyScore: 6,
      metricValue: "Armed",
      lastUpdated: "21:11",
    },
    {
      id: "tank-04",
      label: "Tank-04",
      shortLabel: "T-04",
      type: "Storage tank",
      zoneId: "storage",
      x: 49,
      y: 63,
      status: "watch",
      anomalyScore: 29,
      metricValue: "Humidity drift",
      lastUpdated: "21:14",
    },
    {
      id: "mud-pump-02",
      label: "Mud Pump-02",
      shortLabel: "MP-2",
      type: "Mud pump",
      zoneId: "drilling",
      x: 80,
      y: 63,
      status: "normal",
      anomalyScore: 12,
      metricValue: "Pressure nominal",
      lastUpdated: "21:23",
    },
  ],
  links: [
    { id: "l1", fromAssetId: "compressor-03", toAssetId: "pump-07" },
    { id: "l2", fromAssetId: "pump-07", toAssetId: "generator-02" },
    { id: "l3", fromAssetId: "compressor-03", toAssetId: "gas-sensor-a" },
    { id: "l4", fromAssetId: "valve-12", toAssetId: "tank-04" },
  ],
};
