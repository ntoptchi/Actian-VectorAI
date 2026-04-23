"""Lightweight lat/lon → nearest named place for hotspot labelling.

The hotspot summary used to render as "Hotspot 3 — ~17 km in", which is
internal-coordinate jargon: a teen driver has no mental model for
"km 17 of the trip". Anchoring each hotspot to its nearest named FL
city turns the drawer headline into something a human can actually
picture ("Near Fort Myers").

This is an FL-only approximation — coordinates are city-hall / downtown
points and nearest is computed with an equirectangular distance, which
is accurate to well under 1 km inside Florida and an order of magnitude
cheaper than a proper haversine + geocoder roundtrip. When no city is
within ``max_km`` we return ``None`` and the caller falls back to a
km-into-trip label so we never fabricate a place name.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, radians


@dataclass(frozen=True, slots=True)
class City:
    name: str
    lat: float
    lon: float


# Mirrors routewise/src/lib/cities.ts (same canonical FL picker the
# origin/destination fields use). Kept in Python so the backend can
# label hotspots without reaching across the HTTP boundary.
_FL_CITIES: tuple[City, ...] = (
    City("Altamonte Springs", 28.6611, -81.3656),
    City("Apopka", 28.6934, -81.5322),
    City("Bartow", 27.8964, -81.8431),
    City("Boca Raton", 26.3683, -80.1289),
    City("Bonita Springs", 26.3398, -81.7787),
    City("Boynton Beach", 26.5318, -80.0905),
    City("Bradenton", 27.4989, -82.5748),
    City("Brandon", 27.9378, -82.2859),
    City("Cape Coral", 26.5629, -81.9495),
    City("Clearwater", 27.9659, -82.8001),
    City("Clermont", 28.5494, -81.7729),
    City("Cocoa Beach", 28.3200, -80.6076),
    City("Coconut Creek", 26.2517, -80.1789),
    City("Coral Gables", 25.7215, -80.2684),
    City("Coral Springs", 26.2712, -80.2706),
    City("Crestview", 30.7619, -86.5707),
    City("Davie", 26.0628, -80.2331),
    City("Daytona Beach", 29.2108, -81.0228),
    City("Deerfield Beach", 26.3184, -80.0998),
    City("DeLand", 29.0283, -81.3031),
    City("Delray Beach", 26.4615, -80.0728),
    City("Deltona", 28.9005, -81.2637),
    City("Doral", 25.8195, -80.3553),
    City("Dunedin", 28.0197, -82.7873),
    City("Fort Lauderdale", 26.1224, -80.1373),
    City("Fort Myers", 26.6406, -81.8723),
    City("Fort Pierce", 27.4467, -80.3256),
    City("Fort Walton Beach", 30.4058, -86.6188),
    City("Gainesville", 29.6516, -82.3248),
    City("Hialeah", 25.8576, -80.2781),
    City("Hollywood", 26.0112, -80.1495),
    City("Homestead", 25.4687, -80.4776),
    City("Jacksonville", 30.3322, -81.6557),
    City("Jacksonville Beach", 30.2947, -81.3931),
    City("Jupiter", 26.9342, -80.0942),
    City("Key Largo", 25.0865, -80.4473),
    City("Key West", 24.5551, -81.7800),
    City("Kissimmee", 28.2920, -81.4076),
    City("Lake City", 30.1897, -82.6393),
    City("Lake Mary", 28.7589, -81.3187),
    City("Lake Worth Beach", 26.6168, -80.0684),
    City("Lakeland", 28.0395, -81.9498),
    City("Largo", 27.9095, -82.7873),
    City("Lauderhill", 26.1402, -80.2134),
    City("Leesburg", 28.8108, -81.8779),
    City("Lehigh Acres", 26.6249, -81.6248),
    City("Margate", 26.2445, -80.2059),
    City("Marathon", 24.7137, -81.0904),
    City("Melbourne", 28.0836, -80.6081),
    City("Miami", 25.7617, -80.1918),
    City("Miami Beach", 25.7907, -80.1300),
    City("Miami Gardens", 25.9420, -80.2456),
    City("Miramar", 25.9873, -80.2323),
    City("Naples", 26.1420, -81.7948),
    City("New Port Richey", 28.2441, -82.7193),
    City("Niceville", 30.5163, -86.4823),
    City("North Miami", 25.8901, -80.1867),
    City("North Port", 27.0445, -82.2359),
    City("Ocala", 29.1872, -82.1401),
    City("Ocoee", 28.5694, -81.5439),
    City("Orlando", 28.5383, -81.3792),
    City("Ormond Beach", 29.2858, -81.0559),
    City("Oviedo", 28.6700, -81.2081),
    City("Palatka", 29.6486, -81.6376),
    City("Palm Bay", 28.0345, -80.5887),
    City("Palm Beach Gardens", 26.8235, -80.1387),
    City("Palm Coast", 29.5847, -81.2076),
    City("Palm Harbor", 28.0780, -82.7637),
    City("Panama City", 30.1588, -85.6602),
    City("Panama City Beach", 30.1766, -85.8055),
    City("Pembroke Pines", 26.0078, -80.2962),
    City("Pensacola", 30.4213, -87.2169),
    City("Pinellas Park", 27.8428, -82.6995),
    City("Plant City", 28.0186, -82.1145),
    City("Plantation", 26.1276, -80.2331),
    City("Pompano Beach", 26.2379, -80.1248),
    City("Port Charlotte", 26.9762, -82.0907),
    City("Port Orange", 29.1383, -80.9956),
    City("Port St. Lucie", 27.2939, -80.3503),
    City("Punta Gorda", 26.9298, -82.0454),
    City("Riverview", 27.8661, -82.3265),
    City("Royal Palm Beach", 26.7084, -80.2306),
    City("Sanford", 28.8005, -81.2731),
    City("Sarasota", 27.3364, -82.5307),
    City("Sebastian", 27.8164, -80.4706),
    City("Sebring", 27.4956, -81.4406),
    City("Spring Hill", 28.4769, -82.5232),
    City("St. Augustine", 29.9012, -81.3124),
    City("St. Cloud", 28.2489, -81.2812),
    City("St. Petersburg", 27.7676, -82.6403),
    City("Stuart", 27.1973, -80.2528),
    City("Sunrise", 26.1334, -80.1670),
    City("Tallahassee", 30.4383, -84.2807),
    City("Tamarac", 26.2129, -80.2497),
    City("Tampa", 27.9506, -82.4572),
    City("Tarpon Springs", 28.1461, -82.7565),
    City("Titusville", 28.6122, -80.8076),
    City("Venice", 27.0998, -82.4543),
    City("Vero Beach", 27.6386, -80.3973),
    City("Wellington", 26.6618, -80.2417),
    City("West Palm Beach", 26.7153, -80.0534),
    City("Weston", 26.1003, -80.3998),
    City("Winter Garden", 28.5654, -81.5862),
    City("Winter Haven", 28.0222, -81.7329),
    City("Winter Park", 28.5999, -81.3392),
    City("Winter Springs", 28.6989, -81.2081),
)


def nearest_city(lat: float, lon: float, *, max_km: float = 40.0) -> str | None:
    """Return the name of the closest FL city within ``max_km`` of (lat, lon).

    ``None`` when the nearest city is beyond ``max_km`` (e.g. the segment
    midpoint falls deep in the Everglades or offshore). Equirectangular
    distance is sufficient at FL latitudes and keeps this call O(n) with
    a tight inner loop — fine for the ~6 hotspots per trip-brief.
    """
    cos_lat = cos(radians(lat))
    best_name: str | None = None
    best_km = max_km
    for c in _FL_CITIES:
        dx = (c.lon - lon) * 111.0 * cos_lat
        dy = (c.lat - lat) * 111.0
        d = hypot(dx, dy)
        if d < best_km:
            best_km = d
            best_name = c.name
    return best_name
