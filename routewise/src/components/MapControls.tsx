"use client";

import { useState, type ReactNode } from "react";

export type MapLayers = {
  riskColoring: boolean;
  lessonZones: boolean;
  hotspots: boolean;
  trafficVolume: boolean;
  crashReports: boolean;
};

interface Props {
  layers: MapLayers;
  onToggle: (key: keyof MapLayers) => void;
  flavor: "light" | "dark";
  onFlavorChange: (flavor: "light" | "dark") => void;
  otherRouteOpacity: number;
  onOtherRouteOpacityChange: (value: number) => void;
}

export function MapControls({
  layers,
  onToggle,
  flavor,
  onFlavorChange,
  otherRouteOpacity,
  onOtherRouteOpacityChange,
}: Props) {
  const [panelOpen, setPanelOpen] = useState(false);
  const other = flavor === "light" ? "dark" : "light";
  const viewLabel = layers.trafficVolume ? "Traffic view" : "Risk view";
  return (
    <div
      className="leaflet-bottom leaflet-left"
      style={{ pointerEvents: "auto", zIndex: 1000 }}
    >
      <div
        className="leaflet-control"
        style={{ margin: "0 0 12px 12px", position: "relative" }}
      >
        {panelOpen && (
          <div
            style={{
              position: "absolute",
              bottom: "calc(100% + 8px)",
              left: 0,
              width: 220,
              background: "rgba(15,23,42,0.92)",
              color: "#e2e8f0",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.15)",
              boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
              backdropFilter: "blur(8px)",
              padding: "10px",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
              <input type="checkbox" checked={layers.lessonZones} onChange={() => onToggle("lessonZones")} style={{ accentColor: "#60a5fa" }} />
              <span>Lesson zones</span>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
              <input type="checkbox" checked={layers.hotspots} onChange={() => onToggle("hotspots")} style={{ accentColor: "#60a5fa" }} />
              <span>Danger hotspots</span>
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, cursor: "pointer" }}>
              <input type="checkbox" checked={layers.crashReports} onChange={() => onToggle("crashReports")} style={{ accentColor: "#60a5fa" }} />
              <span>News articles</span>
            </label>
            <div style={{ marginTop: 4 }}>
              <div style={{ fontSize: 11, marginBottom: 6, opacity: 0.8 }}>
                Other route opacity: {Math.round(otherRouteOpacity * 100)}%
              </div>
              <input
                type="range"
                min={15}
                max={90}
                step={5}
                value={Math.round(otherRouteOpacity * 100)}
                onChange={(e) => onOtherRouteOpacityChange(Number(e.target.value) / 100)}
                style={{ width: "100%", accentColor: "#60a5fa" }}
              />
            </div>
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <ControlButton
            onClick={() => setPanelOpen((v) => !v)}
            title="Open overlays panel"
            label="Overlays"
            icon={<LayersIcon />}
          />
          <ControlButton
            onClick={() => onFlavorChange(other)}
            title="Toggle map mode"
            label={flavor === "light" ? "Light mode" : "Dark mode"}
            icon={flavor === "light" ? <TerrainIcon /> : <DarkIcon />}
          />
          <ControlButton
            onClick={() => onToggle(layers.trafficVolume ? "riskColoring" : "trafficVolume")}
            title="Toggle risk/traffic view"
            label={viewLabel}
            icon={<RoadIcon />}
          />
        </div>
      </div>
    </div>
  );
}

function ControlButton({
  onClick,
  title,
  label,
  icon,
}: {
  onClick: () => void;
  title: string;
  label: string;
  icon: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: 44,
        height: 44,
        borderRadius: 10,
        border: "2px solid rgba(255,255,255,0.24)",
        background: "rgba(15,23,42,0.88)",
        color: "#e2e8f0",
        backdropFilter: "blur(8px)",
        cursor: "pointer",
        display: "grid",
        placeItems: "center",
        boxShadow: "0 8px 20px rgba(0,0,0,0.32)",
      }}
      aria-label={label}
    >
      {icon}
    </button>
  );
}

function LayersIcon() {
  return (
    <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3 9 4.5-9 4.5L3 7.5 12 3Z" />
      <path d="m3 12 9 4.5 9-4.5" />
      <path d="m3 16.5 9 4.5 9-4.5" />
    </svg>
  );
}

function RoadIcon() {
  return (
    <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2 8 22" />
      <path d="M14 2 16 22" />
      <path d="M12 7h.01" />
      <path d="M12 12h.01" />
      <path d="M12 17h.01" />
    </svg>
  );
}

function TerrainIcon({ small }: { small?: boolean }) {
  return (
    <svg width={small ? 14 : 18} height={small ? 14 : 18} viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 20 5.5-11L12 15l3-4 6 9H3Z" />
      <path d="M6 7a2 2 0 1 0 4 0 2 2 0 0 0-4 0" />
    </svg>
  );
}

function DarkIcon({ small }: { small?: boolean }) {
  return (
    <svg width={small ? 14 : 18} height={small ? 14 : 18} viewBox="0 0 24 24" fill="none" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
