"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import {
  MapContainer,
  Pane,
  Polyline,
  Tooltip,
  CircleMarker,
  useMap,
} from "react-leaflet";
import { leafletLayer } from "protomaps-leaflet";

import "leaflet/dist/leaflet.css";

const ROUTE_LABEL_STYLE = `
.route-label.leaflet-tooltip {
  background: rgba(11,31,68,0.88);
  color: #fbf6ec;
  border: none;
  border-radius: 6px;
  padding: 4px 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.35);
  font-family: inherit;
  backdrop-filter: blur(4px);
}
.route-label.leaflet-tooltip::before { display: none; }
.route-label--chosen.leaflet-tooltip {
  background: rgba(11,31,68,0.95);
  box-shadow: 0 3px 14px rgba(0,0,0,0.4);
}
`;

import { segmentLocationLabel } from "~/lib/segmentLabels";
import { MapControls, type MapLayers } from "~/components/MapControls";
import type {
  AlternateSummary,
  CrashInsight,
  FatigueStop,
  HotspotSummary,
  LatLon,
  LessonZone,
  NewsCrashPin,
  RiskBand,
  RouteSegment,
} from "~/lib/types";

const RISK_COLOR: Record<RiskBand, string> = {
  low: "#4ade80",
  moderate: "#fbbf24",
  elevated: "#fb923c",
  high: "#ef4444",
};

const RISK_GLOW: Record<RiskBand, string> = {
  low: "rgba(74, 222, 128, 0.35)",
  moderate: "rgba(251, 191, 36, 0.4)",
  elevated: "rgba(251, 146, 60, 0.45)",
  high: "rgba(239, 68, 68, 0.55)",
};

interface Props {
  origin?: LatLon;
  destination?: LatLon;
  segments: RouteSegment[];
  alternates: AlternateSummary[];
  chosenRouteId: string | null;
  hotspots: HotspotSummary[];
  lessonZones: LessonZone[];
  newsCrashes: NewsCrashPin[];
  stops?: FatigueStop[];
  insights: CrashInsight[];
  layers: MapLayers;
  onSegmentClick?: (seg: RouteSegment) => void;
  onHotspotClick?: (h: HotspotSummary) => void;
  onInsightClick?: (i: CrashInsight) => void;
  onLessonZoneClick?: (z: LessonZone) => void;
  onNewsCrashClick?: (n: NewsCrashPin) => void;
  onAlternateClick?: (routeId: string) => void;
  onToggleLayer?: (key: keyof MapLayers) => void;
}

export default function RouteMap({
  origin,
  destination,
  segments,
  alternates,
  chosenRouteId,
  hotspots,
  lessonZones,
  newsCrashes,
  stops,
  insights: _insights,
  layers,
  onSegmentClick,
  onHotspotClick,
  onInsightClick: _onInsightClick,
  onLessonZoneClick,
  onNewsCrashClick,
  onAlternateClick,
  onToggleLayer,
}: Props) {
  const [mapFlavor, setMapFlavor] = useState<MapFlavor>("light");
  const [otherRouteOpacity, setOtherRouteOpacity] = useState(0.4);
  const center = useMemo<[number, number]>(() => {
    if (origin && destination) {
      return [(origin.lat + destination.lat) / 2, (origin.lon + destination.lon) / 2];
    }
    const all = segments.flatMap((s) => s.polyline);
    if (all.length === 0) return [27.7663, -82.6404];
    const mid = all[Math.floor(all.length / 2)];
    if (!mid || mid.length < 2) return [27.7663, -82.6404];
    return [mid[1], mid[0]] as [number, number];
  }, [origin, destination, segments]);

  const bounds = useMemo<L.LatLngBoundsExpression | null>(() => {
    const pts: [number, number][] = segments.flatMap((s) =>
      s.polyline.map(([lon, lat]): [number, number] => [lat, lon]),
    );
    if (origin && destination) {
      pts.push([origin.lat, origin.lon], [destination.lat, destination.lon]);
    }
    if (pts.length < 2) {
      if (origin && destination) {
        return L.latLngBounds(
          [origin.lat, origin.lon],
          [destination.lat, destination.lon],
        );
      }
      return null;
    }
    return L.latLngBounds(pts);
  }, [origin, destination, segments]);

  // Animate risk-colored segments sweeping from origin to destination
  // when crash data first arrives. Progress 0→1 controls how many
  // segments are visible; alternates appear only after the sweep ends.
  const [drawProgress, setDrawProgress] = useState(segments.length > 0 ? 1 : 0);
  const animatedRef = useRef(false);

  useEffect(() => {
    if (segments.length > 0 && !animatedRef.current) {
      animatedRef.current = true;
      const prefersReduced =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (prefersReduced) {
        setDrawProgress(1);
        return;
      }
      let start: number | null = null;
      const DURATION = 800;
      const tick = (ts: number) => {
        start ??= ts;
        const t = Math.min((ts - start) / DURATION, 1);
        setDrawProgress(1 - Math.pow(1 - t, 3));
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }
  }, [segments.length]);

  const visibleSegCount = Math.ceil(segments.length * drawProgress);
  const visibleSegments = segments.slice(0, visibleSegCount);
  const sweepDone = drawProgress >= 1;

  return (
    <MapContainer
      center={center}
      zoom={8}
      minZoom={8}
      scrollWheelZoom
      zoomControl={false}
      className="h-full w-full"
    >
      <MapLayerManager flavor={mapFlavor} />
      <Pane name="alternate-routes" style={{ zIndex: 410 }} />
      <Pane name="alternate-hit" style={{ zIndex: 415 }} />
      <Pane name="lesson-zones" style={{ zIndex: 420 }} />
      <Pane name="chosen-route-glow" style={{ zIndex: 430 }} />
      <Pane name="chosen-route" style={{ zIndex: 440 }} />
      <Pane name="chosen-hit" style={{ zIndex: 445 }} />
      <Pane name="route-labels" style={{ zIndex: 450 }} />
      <Pane name="map-markers" style={{ zIndex: 460 }} />
      {onToggleLayer && (
        <MapControls
          layers={layers}
          onToggle={onToggleLayer}
          flavor={mapFlavor}
          onFlavorChange={setMapFlavor}
          otherRouteOpacity={otherRouteOpacity}
          onOtherRouteOpacityChange={setOtherRouteOpacity}
        />
      )}
      <style dangerouslySetInnerHTML={{ __html: ROUTE_LABEL_STYLE }} />
      <FitBounds bounds={bounds} />

      {/* Origin / destination markers */}
      {origin && (
        <CircleMarker
          pane="map-markers"
          center={[origin.lat, origin.lon]}
          radius={7}
          pathOptions={{ color: "#fff", weight: 2.5, fillColor: "#22c55e", fillOpacity: 1 }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <span className="font-semibold text-paper">Origin</span>
          </Tooltip>
        </CircleMarker>
      )}
      {destination && (
        <CircleMarker
          pane="map-markers"
          center={[destination.lat, destination.lon]}
          radius={7}
          pathOptions={{ color: "#fff", weight: 2.5, fillColor: "#ef4444", fillOpacity: 1 }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <span className="font-semibold text-paper">Destination</span>
          </Tooltip>
        </CircleMarker>
      )}

      {/* Non-chosen alternates: appear after the chosen-route sweep finishes */}
      {sweepDone &&
        alternates
          .filter((a) => a.route_id !== chosenRouteId)
          .flatMap((a) => {
            const segs = a.segments ?? [];
            const allPositions = a.polyline.map(
              ([lon, lat]): [number, number] => [lat, lon],
            );
            const midIdx = Math.floor(allPositions.length / 2);
            const midPoint = allPositions[midIdx] ?? allPositions[0];
            const mins = Math.round(a.duration_s / 60);
            const km = Math.round(a.distance_m / 1000);

            const segLines =
              segs.length > 0
                ? segs.map((seg) => (
                    <Polyline
                      pane="alternate-routes"
                      key={`altseg-${a.route_id}-${seg.segment_id}`}
                      positions={seg.polyline.map(
                        ([lon, lat]): [number, number] => [lat, lon],
                      )}
                      pathOptions={{
                        color: segmentColor(seg, layers),
                        weight: 3,
                        opacity: otherRouteOpacity,
                        lineCap: "round",
                        lineJoin: "round",
                      }}
                      interactive={false}
                    />
                  ))
                : [
                    <Polyline
                      pane="alternate-routes"
                      key={`alt-${a.route_id}`}
                      positions={allPositions}
                      pathOptions={{
                        color: alternateSummaryColor(a, layers),
                        weight: 3,
                        opacity: otherRouteOpacity,
                        dashArray: "5 7",
                      }}
                      interactive={false}
                    />,
                  ];

            return [
              ...segLines,
              // Fat invisible hit-target so thin alternate lines are easy to click
              <Polyline
                pane="alternate-hit"
                key={`althit-${a.route_id}`}
                positions={allPositions}
                pathOptions={{
                  color: "#000",
                  weight: 20,
                  opacity: 0.001,
                  interactive: true,
                }}
                eventHandlers={{
                  click: () => onAlternateClick?.(a.route_id),
                }}
              >
                <Tooltip sticky direction="top" offset={[0, -10]}>
                  <div style={{ fontSize: 11, fontWeight: 500 }}>
                    {km} km · {mins} min ·{" "}
                    <span style={{ color: alternateSummaryColor(a, layers) }}>
                      {RISK_LABEL[a.risk_band]}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, opacity: 0.65 }}>
                    Click to select this route
                  </div>
                </Tooltip>
              </Polyline>,
              // Persistent summary label at route midpoint
              midPoint && (
                <CircleMarker
                  pane="route-labels"
                  key={`altlabel-${a.route_id}`}
                  center={midPoint}
                  radius={0}
                  pathOptions={{ opacity: 0, fillOpacity: 0 }}
                  eventHandlers={{
                    click: () => onAlternateClick?.(a.route_id),
                  }}
                >
                  <Tooltip
                    permanent
                    direction="top"
                    offset={[0, -4]}
                    className="route-label"
                  >
                    <RouteLabel
                      km={km}
                      mins={mins}
                      color={alternateSummaryColor(a, layers)}
                    />
                  </Tooltip>
                </CircleMarker>
              ),
            ];
          })}

      {/* Chosen route summary label at midpoint */}
      {sweepDone && segments.length > 0 && (() => {
        const chosenAlt = alternates.find((a) => a.route_id === chosenRouteId);
        if (!chosenAlt) return null;
        const pts = chosenAlt.polyline.map(
          ([lon, lat]): [number, number] => [lat, lon],
        );
        const mid = pts[Math.floor(pts.length / 2)];
        if (!mid) return null;
        const mins = Math.round(chosenAlt.duration_s / 60);
        const km = Math.round(chosenAlt.distance_m / 1000);
        return (
          <CircleMarker
            pane="route-labels"
            key="chosen-label"
            center={mid}
            radius={0}
            pathOptions={{ opacity: 0, fillOpacity: 0 }}
          >
            <Tooltip
              permanent
              direction="top"
              offset={[0, -4]}
              className="route-label route-label--chosen"
            >
              <RouteLabel
                km={km}
                mins={mins}
                color={alternateSummaryColor(chosenAlt, layers)}
                chosen
              />
            </Tooltip>
          </CircleMarker>
        );
      })()}

      {/* Chosen route — sweeps from origin to destination with risk colors */}
      {visibleSegments.map((seg) => (
        <Polyline
          pane="chosen-route-glow"
          key={`glow-${seg.segment_id}`}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: layers.riskColoring
              && !layers.trafficVolume
              ? RISK_GLOW[seg.risk_band]
              : "rgba(148,163,184,0.28)",
            weight: 9,
            opacity: 0.35,
            lineCap: "round",
            lineJoin: "round",
          }}
          interactive={false}
        />
      ))}
      {visibleSegments.map((seg) => (
        <Polyline
          pane="chosen-route"
          key={seg.segment_id}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: segmentColor(seg, layers),
            weight: seg.risk_band === "low" ? 4 : 5,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
          }}
          interactive={false}
        />
      ))}
      {/* Invisible fat hit-target on top of each segment so the polyline
          is easy to click/hover even when the visual stroke is only 4–5px
          (caught in QA: a 4px line is basically unhittable on a 1080p
          screen, and the underglow has interactive disabled).
          Leaflet drops pointer-events when stroke-opacity is 0, so we
          keep a hairline of opacity (0.001) which still reads as fully
          invisible against the dark map but stays hit-testable. */}
      {sweepDone && segments.map((seg) => (
        <Polyline
          pane="chosen-hit"
          key={`hit-${seg.segment_id}`}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: RISK_COLOR[seg.risk_band],
            weight: 22,
            opacity: 0.001,
            lineCap: "round",
            lineJoin: "round",
            interactive: true,
          }}
          eventHandlers={{
            click: () => onSegmentClick?.(seg),
          }}
        >
          <Tooltip sticky direction="top" offset={[0, -6]}>
            <SegmentTooltip seg={seg} hotspots={hotspots} stops={stops} />
          </Tooltip>
        </Polyline>
      ))}

      {/* Hotspot pins — appear after the route sweep finishes */}
      {sweepDone && layers.lessonZones && lessonZones.map((zone) => (
        <Polyline
          pane="lesson-zones"
          key={zone.zone_id}
          positions={zone.polyline.map(([lon, lat]): [number, number] => [lat, lon])}
          pathOptions={{
            color: "#ffffff",
            weight: 9,
            opacity: 0.95,
            lineCap: "round",
            lineJoin: "round",
            interactive: true,
          }}
          eventHandlers={{
            click: () => onLessonZoneClick?.(zone),
          }}
        >
          <Tooltip sticky direction="top" offset={[0, -8]}>
            <div className="text-[0.6875rem] font-semibold text-paper">{zone.theme_label}</div>
            <div className="text-[0.625rem] uppercase tracking-[0.12em] text-paper/70">
              {zone.from_km.toFixed(0)}-{zone.to_km.toFixed(0)} km
            </div>
          </Tooltip>
        </Polyline>
      ))}

      {sweepDone && layers.hotspots && hotspots.map((h) => (
        <CircleMarker
          pane="map-markers"
          key={h.hotspot_id}
          center={[h.centroid.lat, h.centroid.lon]}
          radius={8}
          pathOptions={{
            color: "#f3ece0",
            weight: 2,
            fillColor: "#b32626",
            fillOpacity: 0.95,
          }}
          eventHandlers={{
            click: () => onHotspotClick?.(h),
          }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <div className="font-semibold text-paper">{h.label}</div>
            <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-paper/70">
              {h.n_crashes} matched · click for briefing
            </div>
          </Tooltip>
        </CircleMarker>
      ))}

      {sweepDone && layers.crashReports && newsCrashes.map((n) => (
        <CircleMarker
          pane="map-markers"
          key={n.crash_id}
          center={[n.lat, n.lon]}
          radius={8}
          pathOptions={{
            color: "#e2e8f0",
            weight: 2,
            fillColor: "#2563eb",
            fillOpacity: 0.95,
          }}
          eventHandlers={{
            click: () => onNewsCrashClick?.(n),
          }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <div style={{ maxWidth: 300 }}>
              <div className="font-semibold text-paper">
                {n.headline}
              </div>
              <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-paper/70">
                News crash report · click for briefing
              </div>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

function segmentColor(seg: RouteSegment, layers: MapLayers): string {
  if (layers.trafficVolume && seg.aadt != null) {
    if (seg.aadt >= 80000) return "#0f172a";
    if (seg.aadt >= 40000) return "#334155";
    if (seg.aadt >= 18000) return "#64748b";
    return "#94a3b8";
  }
  if (layers.riskColoring) return RISK_COLOR[seg.risk_band];
  return "#64748b";
}

function alternateSummaryColor(
  alt: AlternateSummary,
  layers: MapLayers,
): string {
  if (layers.trafficVolume) return "#94a3b8";
  return RISK_COLOR[alt.risk_band];
}

function SegmentTooltip({
  seg,
  hotspots,
  stops,
}: {
  seg: RouteSegment;
  hotspots: HotspotSummary[];
  stops: FatigueStop[] | undefined;
}) {
  const top = seg.top_factors[0];
  // Hover and click must stay consistent — the drawer title uses this
  // same helper, so "km 237 – 248" never leaks back into a tooltip.
  const title = segmentLocationLabel(seg, hotspots, stops);
  return (
    <div className="min-w-48 text-[0.6875rem] leading-relaxed text-paper">
      <div className="flex items-start justify-between gap-3">
        <span className="font-semibold text-paper">{title}</span>
        <span
          className="shrink-0 rounded-sm px-1.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.14em]"
          style={{
            backgroundColor: RISK_COLOR[seg.risk_band],
            color: "#0b1f44",
          }}
        >
          {seg.risk_band}
        </span>
      </div>
      <div className="mt-1.5 text-sm font-medium">
        {seg.n_crashes} matched crash{seg.n_crashes === 1 ? "" : "es"}
        {seg.intensity_ratio != null
          ? ` · ${seg.intensity_ratio.toFixed(1)}× FL avg`
          : ""}
      </div>
      {seg.aadt != null && (
        <div className="text-paper/70">
          AADT {seg.aadt.toLocaleString()}
          {seg.speed_limit_mph != null ? ` · ${seg.speed_limit_mph} mph` : ""}
        </div>
      )}
      {top && (
        <div className="mt-1 border-t border-paper/15 pt-1 text-paper/80">
          Top factor:{" "}
          <span className="font-semibold text-paper">{top.factor}</span>
        </div>
      )}
    </div>
  );
}

const RISK_LABEL: Record<RiskBand, string> = {
  low: "Low",
  moderate: "Moderate",
  elevated: "Elevated",
  high: "High",
};

function RouteLabel({
  km,
  mins,
  color,
  chosen,
}: {
  km: number;
  mins: number;
  color: string;
  chosen?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
        fontWeight: chosen ? 600 : 500,
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          backgroundColor: color,
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: 11, color: chosen ? "#fbf6ec" : "#cdd5e3" }}>
        {km} km · {mins} min
      </span>
    </div>
  );
}

const PMTILES_URL =
  process.env.NEXT_PUBLIC_PMTILES_URL ??
  "http://localhost:8080/tiles/florida.pmtiles";

type MapFlavor = "light" | "dark";

function MapLayerManager({ flavor }: { flavor: MapFlavor }) {
  const map = useMap();
  const [layer, setLayer] = useState<L.Layer | null>(null);

  useEffect(() => {
    if (layer) map.removeLayer(layer);

    const base = leafletLayer({
      url: PMTILES_URL,
      flavor,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }) as unknown as L.Layer & { addTo: (map: L.Map) => unknown; bringToBack: () => void };
    base.addTo(map);
    base.bringToBack();
    setLayer(base);

    return () => {
      map.removeLayer(base);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flavor, map]);

  return null;
}

function FitBounds({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (!bounds) return;
    const isLg = window.matchMedia("(min-width: 1024px)").matches;
    const paddingOptions: L.FitBoundsOptions = {
      paddingTopLeft: [isLg ? 650 : 60, 60] as L.PointTuple,
      paddingBottomRight: [60, 60] as L.PointTuple,
    };
    if (!fitted.current) {
      map.fitBounds(bounds, paddingOptions);
      fitted.current = true;
    } else {
      map.flyToBounds(bounds, { ...paddingOptions, duration: 0.6 });
    }
  }, [bounds, map]);
  return null;
}
