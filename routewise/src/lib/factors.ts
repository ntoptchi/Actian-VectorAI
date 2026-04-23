/**
 * Human-readable labels for backend factor enums.
 *
 * The scoring layer emits lowercase enums ("rear_end", "dark_unlighted",
 * "severity:fatal") because those are the raw tags from FDOT/FARS. The
 * UI used to surface those strings verbatim, which reads as a database
 * dump to anyone who isn't an engineer. This helper maps every enum
 * we know about to plain English and falls back to a title-cased
 * rewrite for anything it doesn't recognise, so a new tag appears as
 * "New Tag" instead of "new_tag".
 */

const FACTOR_LABELS: Record<string, string> = {
  // Crash type
  rear_end: "Rear-end",
  angle: "Angle",
  head_on: "Head-on",
  rollover: "Rollover",
  single_vehicle: "Single-vehicle",
  sideswipe: "Sideswipe",
  pedestrian: "Pedestrian",
  bicycle: "Bicycle",

  // Surface / weather
  dry: "Dry pavement",
  wet: "Wet pavement",
  icy: "Icy pavement",
  snowy: "Snow",
  rain: "Rain",
  fog: "Fog",
  clear: "Clear weather",
  sleet: "Sleet",
  severe_wind: "Severe wind",

  // Lighting
  daylight: "Daylight",
  dawn: "Dawn",
  dusk: "Dusk",
  dark_lighted: "Dark, lit road",
  dark_unlighted: "Dark, unlit road",

  // Severity prefix tags
  "severity:fatal": "Fatal severity",
  "severity:serious": "Serious injury",
  "severity:minor": "Minor injury",
  "severity:pdo": "Property damage only",
};

export function humanizeFactor(factor: string): string {
  const hit = FACTOR_LABELS[factor];
  if (hit) return hit;
  const normalized = factor.replace(/^severity:/, "").replace(/_/g, " ").trim();
  if (!normalized) return factor;
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}
