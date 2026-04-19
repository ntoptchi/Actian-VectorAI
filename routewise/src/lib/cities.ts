/**
 * Florida cities the trip planner can route between.
 *
 * Scope is intentionally Florida-only: the FL DOT crash dataset is the
 * only source feeding the Safety Re-ranker, so a route that leaves the
 * state has nothing useful to surface beyond raw turn-by-turn directions.
 *
 * Coordinates are downtown / city-hall points in WGS84 (lat, lon).
 */

export type City = {
  /** Stable id used as React key. */
  id: string;
  /** Display name without the state, e.g. "Miami". */
  name: string;
  /** USPS state code — kept on the type so the picker can show "Miami, FL". */
  state: string;
  lat: number;
  lon: number;
};

/**
 * Sorted alphabetically so the suggestion list reads naturally without an
 * extra sort pass at render time.
 */
export const CITIES: City[] = [
  { id: "fl-altamonte-springs", name: "Altamonte Springs", state: "FL", lat: 28.6611, lon: -81.3656 },
  { id: "fl-apopka", name: "Apopka", state: "FL", lat: 28.6934, lon: -81.5322 },
  { id: "fl-bartow", name: "Bartow", state: "FL", lat: 27.8964, lon: -81.8431 },
  { id: "fl-boca-raton", name: "Boca Raton", state: "FL", lat: 26.3683, lon: -80.1289 },
  { id: "fl-bonita-springs", name: "Bonita Springs", state: "FL", lat: 26.3398, lon: -81.7787 },
  { id: "fl-boynton-beach", name: "Boynton Beach", state: "FL", lat: 26.5318, lon: -80.0905 },
  { id: "fl-bradenton", name: "Bradenton", state: "FL", lat: 27.4989, lon: -82.5748 },
  { id: "fl-brandon", name: "Brandon", state: "FL", lat: 27.9378, lon: -82.2859 },
  { id: "fl-cape-coral", name: "Cape Coral", state: "FL", lat: 26.5629, lon: -81.9495 },
  { id: "fl-clearwater", name: "Clearwater", state: "FL", lat: 27.9659, lon: -82.8001 },
  { id: "fl-clermont", name: "Clermont", state: "FL", lat: 28.5494, lon: -81.7729 },
  { id: "fl-cocoa-beach", name: "Cocoa Beach", state: "FL", lat: 28.3200, lon: -80.6076 },
  { id: "fl-coconut-creek", name: "Coconut Creek", state: "FL", lat: 26.2517, lon: -80.1789 },
  { id: "fl-coral-gables", name: "Coral Gables", state: "FL", lat: 25.7215, lon: -80.2684 },
  { id: "fl-coral-springs", name: "Coral Springs", state: "FL", lat: 26.2712, lon: -80.2706 },
  { id: "fl-crestview", name: "Crestview", state: "FL", lat: 30.7619, lon: -86.5707 },
  { id: "fl-davie", name: "Davie", state: "FL", lat: 26.0628, lon: -80.2331 },
  { id: "fl-daytona-beach", name: "Daytona Beach", state: "FL", lat: 29.2108, lon: -81.0228 },
  { id: "fl-deerfield-beach", name: "Deerfield Beach", state: "FL", lat: 26.3184, lon: -80.0998 },
  { id: "fl-deland", name: "DeLand", state: "FL", lat: 29.0283, lon: -81.3031 },
  { id: "fl-delray-beach", name: "Delray Beach", state: "FL", lat: 26.4615, lon: -80.0728 },
  { id: "fl-deltona", name: "Deltona", state: "FL", lat: 28.9005, lon: -81.2637 },
  { id: "fl-doral", name: "Doral", state: "FL", lat: 25.8195, lon: -80.3553 },
  { id: "fl-dunedin", name: "Dunedin", state: "FL", lat: 28.0197, lon: -82.7873 },
  { id: "fl-fort-lauderdale", name: "Fort Lauderdale", state: "FL", lat: 26.1224, lon: -80.1373 },
  { id: "fl-fort-myers", name: "Fort Myers", state: "FL", lat: 26.6406, lon: -81.8723 },
  { id: "fl-fort-pierce", name: "Fort Pierce", state: "FL", lat: 27.4467, lon: -80.3256 },
  { id: "fl-fort-walton-beach", name: "Fort Walton Beach", state: "FL", lat: 30.4058, lon: -86.6188 },
  { id: "fl-gainesville", name: "Gainesville", state: "FL", lat: 29.6516, lon: -82.3248 },
  { id: "fl-hialeah", name: "Hialeah", state: "FL", lat: 25.8576, lon: -80.2781 },
  { id: "fl-hollywood", name: "Hollywood", state: "FL", lat: 26.0112, lon: -80.1495 },
  { id: "fl-homestead", name: "Homestead", state: "FL", lat: 25.4687, lon: -80.4776 },
  { id: "fl-jacksonville", name: "Jacksonville", state: "FL", lat: 30.3322, lon: -81.6557 },
  { id: "fl-jacksonville-beach", name: "Jacksonville Beach", state: "FL", lat: 30.2947, lon: -81.3931 },
  { id: "fl-jupiter", name: "Jupiter", state: "FL", lat: 26.9342, lon: -80.0942 },
  { id: "fl-key-largo", name: "Key Largo", state: "FL", lat: 25.0865, lon: -80.4473 },
  { id: "fl-key-west", name: "Key West", state: "FL", lat: 24.5551, lon: -81.7800 },
  { id: "fl-kissimmee", name: "Kissimmee", state: "FL", lat: 28.2920, lon: -81.4076 },
  { id: "fl-lake-city", name: "Lake City", state: "FL", lat: 30.1897, lon: -82.6393 },
  { id: "fl-lake-mary", name: "Lake Mary", state: "FL", lat: 28.7589, lon: -81.3187 },
  { id: "fl-lake-worth-beach", name: "Lake Worth Beach", state: "FL", lat: 26.6168, lon: -80.0684 },
  { id: "fl-lakeland", name: "Lakeland", state: "FL", lat: 28.0395, lon: -81.9498 },
  { id: "fl-largo", name: "Largo", state: "FL", lat: 27.9095, lon: -82.7873 },
  { id: "fl-lauderhill", name: "Lauderhill", state: "FL", lat: 26.1402, lon: -80.2134 },
  { id: "fl-leesburg", name: "Leesburg", state: "FL", lat: 28.8108, lon: -81.8779 },
  { id: "fl-lehigh-acres", name: "Lehigh Acres", state: "FL", lat: 26.6249, lon: -81.6248 },
  { id: "fl-margate", name: "Margate", state: "FL", lat: 26.2445, lon: -80.2059 },
  { id: "fl-marathon", name: "Marathon", state: "FL", lat: 24.7137, lon: -81.0904 },
  { id: "fl-melbourne", name: "Melbourne", state: "FL", lat: 28.0836, lon: -80.6081 },
  { id: "fl-miami", name: "Miami", state: "FL", lat: 25.7617, lon: -80.1918 },
  { id: "fl-miami-beach", name: "Miami Beach", state: "FL", lat: 25.7907, lon: -80.1300 },
  { id: "fl-miami-gardens", name: "Miami Gardens", state: "FL", lat: 25.9420, lon: -80.2456 },
  { id: "fl-miramar", name: "Miramar", state: "FL", lat: 25.9873, lon: -80.2323 },
  { id: "fl-naples", name: "Naples", state: "FL", lat: 26.1420, lon: -81.7948 },
  { id: "fl-new-port-richey", name: "New Port Richey", state: "FL", lat: 28.2441, lon: -82.7193 },
  { id: "fl-niceville", name: "Niceville", state: "FL", lat: 30.5163, lon: -86.4823 },
  { id: "fl-north-miami", name: "North Miami", state: "FL", lat: 25.8901, lon: -80.1867 },
  { id: "fl-north-port", name: "North Port", state: "FL", lat: 27.0445, lon: -82.2359 },
  { id: "fl-ocala", name: "Ocala", state: "FL", lat: 29.1872, lon: -82.1401 },
  { id: "fl-ocoee", name: "Ocoee", state: "FL", lat: 28.5694, lon: -81.5439 },
  { id: "fl-orlando", name: "Orlando", state: "FL", lat: 28.5383, lon: -81.3792 },
  { id: "fl-ormond-beach", name: "Ormond Beach", state: "FL", lat: 29.2858, lon: -81.0559 },
  { id: "fl-oviedo", name: "Oviedo", state: "FL", lat: 28.6700, lon: -81.2081 },
  { id: "fl-palatka", name: "Palatka", state: "FL", lat: 29.6486, lon: -81.6376 },
  { id: "fl-palm-bay", name: "Palm Bay", state: "FL", lat: 28.0345, lon: -80.5887 },
  { id: "fl-palm-beach-gardens", name: "Palm Beach Gardens", state: "FL", lat: 26.8235, lon: -80.1387 },
  { id: "fl-palm-coast", name: "Palm Coast", state: "FL", lat: 29.5847, lon: -81.2076 },
  { id: "fl-palm-harbor", name: "Palm Harbor", state: "FL", lat: 28.0780, lon: -82.7637 },
  { id: "fl-panama-city", name: "Panama City", state: "FL", lat: 30.1588, lon: -85.6602 },
  { id: "fl-panama-city-beach", name: "Panama City Beach", state: "FL", lat: 30.1766, lon: -85.8055 },
  { id: "fl-pembroke-pines", name: "Pembroke Pines", state: "FL", lat: 26.0078, lon: -80.2962 },
  { id: "fl-pensacola", name: "Pensacola", state: "FL", lat: 30.4213, lon: -87.2169 },
  { id: "fl-pinellas-park", name: "Pinellas Park", state: "FL", lat: 27.8428, lon: -82.6995 },
  { id: "fl-plant-city", name: "Plant City", state: "FL", lat: 28.0186, lon: -82.1145 },
  { id: "fl-plantation", name: "Plantation", state: "FL", lat: 26.1276, lon: -80.2331 },
  { id: "fl-pompano-beach", name: "Pompano Beach", state: "FL", lat: 26.2379, lon: -80.1248 },
  { id: "fl-port-charlotte", name: "Port Charlotte", state: "FL", lat: 26.9762, lon: -82.0907 },
  { id: "fl-port-orange", name: "Port Orange", state: "FL", lat: 29.1383, lon: -80.9956 },
  { id: "fl-port-st-lucie", name: "Port St. Lucie", state: "FL", lat: 27.2939, lon: -80.3503 },
  { id: "fl-punta-gorda", name: "Punta Gorda", state: "FL", lat: 26.9298, lon: -82.0454 },
  { id: "fl-riverview", name: "Riverview", state: "FL", lat: 27.8661, lon: -82.3265 },
  { id: "fl-royal-palm-beach", name: "Royal Palm Beach", state: "FL", lat: 26.7084, lon: -80.2306 },
  { id: "fl-sanford", name: "Sanford", state: "FL", lat: 28.8005, lon: -81.2731 },
  { id: "fl-sarasota", name: "Sarasota", state: "FL", lat: 27.3364, lon: -82.5307 },
  { id: "fl-sebastian", name: "Sebastian", state: "FL", lat: 27.8164, lon: -80.4706 },
  { id: "fl-sebring", name: "Sebring", state: "FL", lat: 27.4956, lon: -81.4406 },
  { id: "fl-spring-hill", name: "Spring Hill", state: "FL", lat: 28.4769, lon: -82.5232 },
  { id: "fl-st-augustine", name: "St. Augustine", state: "FL", lat: 29.9012, lon: -81.3124 },
  { id: "fl-st-cloud", name: "St. Cloud", state: "FL", lat: 28.2489, lon: -81.2812 },
  { id: "fl-st-petersburg", name: "St. Petersburg", state: "FL", lat: 27.7676, lon: -82.6403 },
  { id: "fl-stuart", name: "Stuart", state: "FL", lat: 27.1973, lon: -80.2528 },
  { id: "fl-sunrise", name: "Sunrise", state: "FL", lat: 26.1334, lon: -80.1670 },
  { id: "fl-tallahassee", name: "Tallahassee", state: "FL", lat: 30.4383, lon: -84.2807 },
  { id: "fl-tamarac", name: "Tamarac", state: "FL", lat: 26.2129, lon: -80.2497 },
  { id: "fl-tampa", name: "Tampa", state: "FL", lat: 27.9506, lon: -82.4572 },
  { id: "fl-tarpon-springs", name: "Tarpon Springs", state: "FL", lat: 28.1461, lon: -82.7565 },
  { id: "fl-titusville", name: "Titusville", state: "FL", lat: 28.6122, lon: -80.8076 },
  { id: "fl-venice", name: "Venice", state: "FL", lat: 27.0998, lon: -82.4543 },
  { id: "fl-vero-beach", name: "Vero Beach", state: "FL", lat: 27.6386, lon: -80.3973 },
  { id: "fl-wellington", name: "Wellington", state: "FL", lat: 26.6618, lon: -80.2417 },
  { id: "fl-west-palm-beach", name: "West Palm Beach", state: "FL", lat: 26.7153, lon: -80.0534 },
  { id: "fl-weston", name: "Weston", state: "FL", lat: 26.1003, lon: -80.3998 },
  { id: "fl-winter-garden", name: "Winter Garden", state: "FL", lat: 28.5654, lon: -81.5862 },
  { id: "fl-winter-haven", name: "Winter Haven", state: "FL", lat: 28.0222, lon: -81.7329 },
  { id: "fl-winter-park", name: "Winter Park", state: "FL", lat: 28.5999, lon: -81.3392 },
  { id: "fl-winter-springs", name: "Winter Springs", state: "FL", lat: 28.6989, lon: -81.2081 },
];

/** O(1) coord lookup by id. */
export const CITY_BY_ID: ReadonlyMap<string, City> = new Map(
  CITIES.map((c) => [c.id, c]),
);

/** "Miami, FL" — kept tiny so search matchers can call it freely. */
export function cityLabel(c: City): string {
  return `${c.name}, ${c.state}`;
}

/**
 * Substring + word-prefix search over the curated list.
 *
 * - Ranks word-start matches above mid-word matches so "tam" surfaces
 *   "Tampa" / "Tamarac" before "Altamonte Springs".
 * - Returns up to `limit` results so the suggestion popover stays light.
 * - Empty query → empty array (caller hides the popover).
 */
export function searchCities(query: string, limit = 8): City[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];

  type Scored = { city: City; score: number };
  const scored: Scored[] = [];
  for (const c of CITIES) {
    const name = c.name.toLowerCase();
    const label = cityLabel(c).toLowerCase();
    let score = -1;
    if (name === q) score = 100;
    else if (name.startsWith(q)) score = 80;
    else if (label.startsWith(q)) score = 70;
    else {
      // Prefer matches that align with a word boundary (after a space or
      // punctuation) — beats burying "St. Petersburg" under "Pinellas Park"
      // when the user types "pe".
      const wordBoundary = name.split(/[\s.\-]+/).some((w) => w.startsWith(q));
      if (wordBoundary) score = 50;
      else if (name.includes(q)) score = 20;
    }
    if (score >= 0) scored.push({ city: c, score });
  }

  scored.sort((a, b) => b.score - a.score || a.city.name.localeCompare(b.city.name));
  return scored.slice(0, limit).map((s) => s.city);
}
