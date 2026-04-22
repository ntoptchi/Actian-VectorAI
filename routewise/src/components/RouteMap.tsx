"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
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
  NewsArticle,
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
  newsArticles: NewsArticle[];
  onSegmentClick?: (seg: RouteSegment) => void;
  onHotspotClick?: (h: HotspotSummary) => void;
  onNewsClick?: (n: NewsArticle) => void;
}

export default function RouteMap({
  segments,
  alternates,
  chosenRouteId,
  hotspots,
  stops,
  newsArticles,
  onSegmentClick,
  onHotspotClick,
  onNewsClick,
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

      {/* News article pins — distinct diamond shape via rotated square */}
      {newsArticles.map((n) => (
        <CircleMarker
          key={n.article_id}
          center={[n.location.lat, n.location.lon]}
          radius={7}
          pathOptions={{
            color: "#f3ece0",
            weight: 2,
            fillColor: "#2563eb",
            fillOpacity: 0.95,
          }}
          eventHandlers={{
            click: () => onNewsClick?.(n),
          }}
        >
          <Tooltip direction="top" offset={[0, -6]}>
            <div className="max-w-[16rem] font-semibold text-paper">
              {n.headline}
            </div>
            <div className="text-[0.6875rem] uppercase tracking-[0.14em] text-paper/70">
              {n.publisher}
              {n.publish_date ? ` · ${n.publish_date}` : ""} · click to read
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

type MapStyle = "terrain" | "satellite";

const MAP_STYLES: Record<MapStyle, { url: string; attribution: string; subdomains?: string }> = {
  terrain: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: '&copy; Esri &mdash; Esri, Maxar, Earthstar Geographics',
  },
};

function MapLayerSwitcher() {
  const map = useMap();
  const [style, setStyle] = useState<MapStyle>("terrain");
  const [open, setOpen] = useState(false);
  const [layers, setLayers] = useState<L.TileLayer[]>([]);

  useEffect(() => {
    layers.forEach((l) => map.removeLayer(l));

    const cfg = MAP_STYLES[style];
    const base = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: 19,
      ...(cfg.subdomains ? { subdomains: cfg.subdomains } : {}),
    });
    base.addTo(map);
    base.bringToBack();

    const newLayers: L.TileLayer[] = [base];

    // Add a labels overlay on satellite so streets/places are readable
    if (style === "satellite") {
      const labels = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 19, pane: "shadowPane" },
      );
      labels.addTo(map);
      newLayers.push(labels);

      const places = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        { maxZoom: 19, pane: "shadowPane" },
      );
      places.addTo(map);
      newLayers.push(places);
    }

    setLayers(newLayers);
    return () => {
      newLayers.forEach((l) => map.removeLayer(l));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [style, map]);

  const pick = useCallback((s: MapStyle) => {
    setStyle(s);
    setOpen(false);
  }, []);

  const other: MapStyle = style === "terrain" ? "satellite" : "terrain";

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
          {style === "terrain" ? <TerrainIcon /> : <SatelliteIcon />}
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
            title={other === "satellite" ? "Satellite" : "Terrain"}
          >
            {other === "satellite" ? <SatelliteIcon /> : <TerrainIcon />}
          </button>
        </div>
      </div>
    </div>
  );
}

function LayersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2 2 7l10 5 10-5-10-5Z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </svg>
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

function SatelliteIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20" />
      <path d="M12 2a14.5 14.5 0 0 1 0 20" />
      <path d="M2 12h20" />
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
