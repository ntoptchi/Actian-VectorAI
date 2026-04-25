"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import L from "leaflet";
import {
  MapContainer,
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
import type {
  AlternateSummary,
  CrashInsight,
  FatigueStop,
  HotspotSummary,
  LatLon,
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
  stops?: FatigueStop[];
  insights: CrashInsight[];
  onSegmentClick?: (seg: RouteSegment) => void;
  onHotspotClick?: (h: HotspotSummary) => void;
  onInsightClick?: (i: CrashInsight) => void;
  onAlternateClick?: (routeId: string) => void;
}

export default function RouteMap({
  origin,
  destination,
  segments,
  alternates,
  chosenRouteId,
  hotspots,
  stops,
  insights,
  onSegmentClick,
  onHotspotClick,
  onInsightClick,
  onAlternateClick,
}: Props) {
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
        if (start === null) start = ts;
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
      <MapLayerSwitcher />
      <style dangerouslySetInnerHTML={{ __html: ROUTE_LABEL_STYLE }} />
      <FitBounds bounds={bounds} />

      {/* Origin / destination markers */}
      {origin && (
        <CircleMarker
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
                      key={`altseg-${a.route_id}-${seg.segment_id}`}
                      positions={seg.polyline.map(
                        ([lon, lat]): [number, number] => [lat, lon],
                      )}
                      pathOptions={{
                        color: RISK_COLOR[seg.risk_band],
                        weight: 3,
                        opacity: 0.4,
                        lineCap: "round",
                        lineJoin: "round",
                      }}
                      interactive={false}
                    />
                  ))
                : [
                    <Polyline
                      key={`alt-${a.route_id}`}
                      positions={allPositions}
                      pathOptions={{
                        color: "#5b8fc4",
                        weight: 3,
                        opacity: 0.35,
                        dashArray: "5 7",
                      }}
                      interactive={false}
                    />,
                  ];

            return [
              ...segLines,
              // Fat invisible hit-target so thin alternate lines are easy to click
              <Polyline
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
                    <span style={{ color: RISK_COLOR[a.risk_band] }}>
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
                    <RouteLabel km={km} mins={mins} band={a.risk_band} />
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
              <RouteLabel km={km} mins={mins} band={chosenAlt.risk_band} chosen />
            </Tooltip>
          </CircleMarker>
        );
      })()}

      {/* Chosen route — sweeps from origin to destination with risk colors */}
      {visibleSegments.map((seg) => (
        <Polyline
          key={`glow-${seg.segment_id}`}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: RISK_GLOW[seg.risk_band],
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
          key={seg.segment_id}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: RISK_COLOR[seg.risk_band],
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
      {sweepDone && hotspots.map((h) => (
        <CircleMarker
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

      {/* Insight pins — amber "lesson" markers, distinct from the
          red hotspot pins so a glance separates "a cluster of crashes
          here tonight" from "here's a lesson that applies along this
          stretch". Pin location is the *segment midpoint* from the
          retrieval service, not the article's original lat/lon, so
          pins always sit on the route rather than floating off it. */}
      {sweepDone && insights.map((ins) => (
        <CircleMarker
          key={ins.insight_id}
          center={[ins.pin_location.lat, ins.pin_location.lon]}
          radius={7}
          pathOptions={{
            color: "#f3ece0",
            weight: 2,
            fillColor: "#d97706",
            fillOpacity: 0.95,
          }}
          eventHandlers={{
            click: () => onInsightClick?.(ins),
          }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <div style={{ maxWidth: 300 }}>
              <div className="font-semibold text-paper">
                {ins.headline}
              </div>
              <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-paper/70">
                Lesson from a past crash · click to read
              </div>
            </div>
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
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
    <div className="min-w-[12rem] text-[0.6875rem] leading-relaxed text-paper">
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
  band,
  chosen,
}: {
  km: number;
  mins: number;
  band: RiskBand;
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
          backgroundColor: RISK_COLOR[band],
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

function MapLayerSwitcher() {
  const map = useMap();
  const [flavor, setFlavor] = useState<MapFlavor>("light");
  const [open, setOpen] = useState(false);
  const [layer, setLayer] = useState<L.Layer | null>(null);

  useEffect(() => {
    if (layer) map.removeLayer(layer);

    const base = leafletLayer({
      url: PMTILES_URL,
      flavor,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
    base.addTo(map);
    base.bringToBack();
    setLayer(base);

    return () => {
      map.removeLayer(base);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flavor, map]);

  const pick = useCallback((f: MapFlavor) => {
    setFlavor(f);
    setOpen(false);
  }, []);

  const other: MapFlavor = flavor === "light" ? "dark" : "light";

  return (
    <div
      className="leaflet-bottom leaflet-right"
      style={{ pointerEvents: "auto", zIndex: 1000 }}
    >
      <div
        className="leaflet-control"
        style={{ margin: "0 10px 10px 0", display: "flex", flexDirection: "column-reverse", alignItems: "center", gap: 0 }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        {/* Current style icon */}
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            width: 40,
            height: 40,
            borderRadius: 8,
            border: "2px solid rgba(255,255,255,0.25)",
            background: "rgba(15,23,42,0.85)",
            backdropFilter: "blur(8px)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}
          title="Switch map style"
        >
          {flavor === "light" ? <TerrainIcon /> : <DarkIcon />}
        </button>

        {/* The other option slides in directly below */}
        <div
          style={{
            overflow: "hidden",
            maxHeight: open ? 44 : 0,
            opacity: open ? 1 : 0,
            transition: "max-height 0.2s ease, opacity 0.15s ease",
          }}
        >
          <button
            onClick={() => pick(other)}
            style={{
              marginBottom: 4,
              width: 40,
              height: 40,
              borderRadius: 8,
              border: "2px solid rgba(255,255,255,0.15)",
              background: "rgba(15,23,42,0.85)",
              backdropFilter: "blur(8px)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            }}
            title={other === "dark" ? "Dark" : "Light"}
          >
            {other === "dark" ? <DarkIcon /> : <TerrainIcon />}
          </button>
        </div>
      </div>
    </div>
  );
}

function TerrainIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 20 5.5-11L12 15l3-4 6 9H3Z" />
      <path d="M6 7a2 2 0 1 0 4 0 2 2 0 0 0-4 0" />
    </svg>
  );
}

function DarkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
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
