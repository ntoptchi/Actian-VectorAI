"use client";

import { useEffect, useMemo } from "react";
import L from "leaflet";
import {
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  CircleMarker,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { segmentLocationLabel } from "~/lib/segmentLabels";
import type {
  AlternateSummary,
  FatigueStop,
  HotspotSummary,
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
  segments: RouteSegment[];
  alternates: AlternateSummary[];
  chosenRouteId: string | null;
  hotspots: HotspotSummary[];
  stops?: FatigueStop[];
  onSegmentClick?: (seg: RouteSegment) => void;
  onHotspotClick?: (h: HotspotSummary) => void;
}

export default function RouteMap({
  segments,
  alternates,
  chosenRouteId,
  hotspots,
  stops,
  onSegmentClick,
  onHotspotClick,
}: Props) {
  const center = useMemo<[number, number]>(() => {
    const all = segments.flatMap((s) => s.polyline);
    if (all.length === 0) return [27.7663, -82.6404];
    const mid = all[Math.floor(all.length / 2)];
    if (!mid || mid.length < 2) return [27.7663, -82.6404];
    return [mid[1], mid[0]] as [number, number];
  }, [segments]);

  const bounds = useMemo<L.LatLngBoundsExpression | null>(() => {
    const pts: [number, number][] = segments.flatMap((s) =>
      s.polyline.map(([lon, lat]): [number, number] => [lat, lon]),
    );
    if (pts.length < 2) return null;
    return L.latLngBounds(pts);
  }, [segments]);

  return (
    <MapContainer
      center={center}
      zoom={8}
      scrollWheelZoom
      zoomControl={false}
      className="h-full w-full"
    >
      {/* Dark editorial tiles — matches the satellite/topographic mockup vibe */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={19}
      />
      {/* Place labels on top so the route reads cleanly */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={19}
        opacity={0.7}
      />
      <FitBounds bounds={bounds} />

      {/* Faded alternates underneath */}
      {alternates
        .filter((a) => a.route_id !== chosenRouteId)
        .map((a) => (
          <Polyline
            key={`alt-${a.route_id}`}
            positions={a.polyline.map(([lon, lat]) => [lat, lon])}
            pathOptions={{
              color: "#5b8fc4",
              weight: 3,
              opacity: 0.55,
              dashArray: "5 7",
            }}
          />
        ))}

      {/* Chosen route — colored per segment with a soft underglow */}
      {segments.map((seg) => (
        <Polyline
          key={`glow-${seg.segment_id}`}
          positions={seg.polyline.map(([lon, lat]) => [lat, lon])}
          pathOptions={{
            color: RISK_GLOW[seg.risk_band],
            weight: 12,
            opacity: 0.65,
            lineCap: "round",
            lineJoin: "round",
          }}
          interactive={false}
        />
      ))}
      {segments.map((seg) => (
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
      {segments.map((seg) => (
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

      {/* Hotspot pins */}
      {hotspots.map((h) => (
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

function FitBounds({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [60, 60] });
    }
  }, [bounds, map]);
  return null;
}
