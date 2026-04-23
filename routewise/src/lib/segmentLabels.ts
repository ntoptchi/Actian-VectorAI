import type { FatigueStop, HotspotSummary, RouteSegment } from "~/lib/types";

/**
 * Build a human-readable segment headline used by both the drawer card
 * and the map-hover tooltip, so they never drift out of sync.
 *
 * Raw "km 237.0 – 248.3" is an internal coordinate — a teen driver has
 * no idea where km 237 is. We anchor every segment to the nearest named
 * landmark in the trip response (a hotspot label, a hotspot road_name,
 * or a fatigue-plan suggested stop). No distance threshold:
 * "Near Fort Myers · I-75 NB" is more useful than any km coordinate,
 * and a road label stays valid across long interstate stretches.
 */
export function segmentLocationLabel(
  s: RouteSegment,
  hotspots: HotspotSummary[] | undefined,
  stops: FatigueStop[] | undefined,
): string {
  const midKm = (s.from_km + s.to_km) / 2;
  const nearestHot = nearestByKm(hotspots, midKm, (h) => h.km_into_trip);
  const nearestStop = nearestByKm(stops, midKm, (st) => st.km_into_trip);

  const hotDist = nearestHot
    ? Math.abs(nearestHot.km_into_trip - midKm)
    : Infinity;
  const stopDist = nearestStop
    ? Math.abs(nearestStop.km_into_trip - midKm)
    : Infinity;

  // Place = whichever anchor is closest. Road always comes from the
  // nearest hotspot (stops don't carry a road name).
  const road = nearestHot
    ? (nearestHot.road_name ?? extractRoadFromLabel(nearestHot.label))
    : null;
  const place =
    hotDist <= stopDist && nearestHot
      ? (extractPlaceFromLabel(nearestHot.label) ?? nearestHot.road_name)
      : (nearestStop?.label ?? null);

  if (place && road && place !== road) return `Near ${place} · ${road}`;
  if (place) return `Near ${place}`;
  if (road) return `Along ${road}`;
  return "Stretch along the route";
}

function nearestByKm<T>(
  items: T[] | undefined,
  km: number,
  getKm: (t: T) => number,
): T | null {
  if (!items || items.length === 0) return null;
  const first = items[0];
  if (first === undefined) return null;
  let best: T = first;
  let bestDelta = Math.abs(getKm(best) - km);
  for (const item of items) {
    const d = Math.abs(getKm(item) - km);
    if (d < bestDelta) {
      bestDelta = d;
      best = item;
    }
  }
  return best;
}

// Labels can take two shapes:
//   * "I-75 NB approaching Exit 136, Fort Myers"  (legacy — road, place)
//   * "Near Fort Myers"                           (new — named city only)
// The second form is what the backend emits now that hotspots are
// anchored to the nearest FL city. Detect and strip the "Near " prefix
// so the place extractor returns just the bare city name, and the road
// extractor returns null (no road info available in the short form).
function extractRoadFromLabel(label: string): string | null {
  if (/^near\s+/i.test(label)) return null;
  const [road] = label.split(",");
  return road?.trim() || null;
}

function extractPlaceFromLabel(label: string): string | null {
  const nearMatch = label.match(/^near\s+(.+)$/i);
  if (nearMatch) return nearMatch[1]?.trim() || null;
  const idx = label.indexOf(",");
  if (idx < 0) return null;
  return label.slice(idx + 1).trim() || null;
}
