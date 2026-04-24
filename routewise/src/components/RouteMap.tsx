"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
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

import { segmentLocationLabel } from "~/lib/segmentLabels";
import type {
  AlternateSummary,
  CrashInsight,
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
  insights: CrashInsight[];
  onSegmentClick?: (seg: RouteSegment) => void;
  onHotspotClick?: (h: HotspotSummary) => void;
  onInsightClick?: (i: CrashInsight) => void;
}

export default function RouteMap({
  segments,
  alternates,
  chosenRouteId,
  hotspots,
  stops,
  insights,
  onSegmentClick,
  onHotspotClick,
  onInsightClick,
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
      <MapLayerSwitcher />
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

      {/* Insight pins — amber "lesson" markers, distinct from the
          red hotspot pins so a glance separates "a cluster of crashes
          here tonight" from "here's a lesson that applies along this
          stretch". Pin location is the *segment midpoint* from the
          retrieval service, not the article's original lat/lon, so
          pins always sit on the route rather than floating off it. */}
      {insights.map((ins) => (
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
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [60, 60] });
    }
  }, [bounds, map]);
  return null;
}
