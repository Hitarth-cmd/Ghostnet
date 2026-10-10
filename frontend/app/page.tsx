"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { Detection, EcologicalAlert, FeatureCollection } from "@/types";
import DetectionPanel from "@/components/DetectionPanel";
import LayerToggle from "@/components/LayerToggle";
import ResponderPortal from "@/components/ResponderPortal";
import EcologicalAlertBanner from "@/components/EcologicalAlertBanner";
import DataSourcesModal from "@/components/DataSourcesModal";
import ChatWidget from "@/components/ChatWidget";

// Dynamic import for MapLibre
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const EMPTY_FC: FeatureCollection = { type: "FeatureCollection", features: [] };

export default function DashboardPage() {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [ecologicalAlerts, setEcologicalAlerts] = useState<EcologicalAlert[]>([]);

  // Map FeatureCollections
  const [detectionsFC, setDetectionsFC] = useState<FeatureCollection>(EMPTY_FC);
  const [trajectoriesFC, setTrajectoriesFC] = useState<FeatureCollection>(EMPTY_FC);
  const [riskZonesFC, setRiskZonesFC] = useState<FeatureCollection>(EMPTY_FC);
  const [protectedAreasFC, setProtectedAreasFC] = useState<FeatureCollection>(EMPTY_FC);
  const [habitatsFC, setHabitatsFC] = useState<FeatureCollection>(EMPTY_FC);
  const [coralReefsFC, setCoralReefsFC] = useState<FeatureCollection>(EMPTY_FC);
  const [speciesHabitatsFC, setSpeciesHabitatsFC] = useState<FeatureCollection>(EMPTY_FC);
  const [alertsFC, setAlertsFC] = useState<FeatureCollection>(EMPTY_FC);

  // Selection & UI States
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);
  const [mapCenterCoords, setMapCenterCoords] = useState<[number, number] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Theme state: "light" (default) or "dark"
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("oceanguard_theme") as "light" | "dark" | null;
      if (saved) {
        setTheme(saved);
      }
    } catch {}
  }, []);

  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    try {
      localStorage.setItem("oceanguard_theme", next);
    } catch {}
  };

  // Modals
  const [isResponderPortalOpen, setIsResponderPortalOpen] = useState(false);
  const [isDataSourcesOpen, setIsDataSourcesOpen] = useState(false);

  // Chat overlay from Debris Route Assistant
  const [chatOverlayFC, setChatOverlayFC] = useState<GeoJSON.FeatureCollection | null>(null);

  // Filters
  const [filterMode, setFilterMode] = useState<"all" | "actionable" | "review" | "assigned">("all");

  // Visible Layers
  const [visibleLayers, setVisibleLayers] = useState<Record<string, boolean>>({
    detections: true,
    trajectories: true,
    coralReefs: true,
    speciesHabitats: true,
    protectedAreas: true,
    riskZones: true,
    ecologicalAlerts: true,
  });

  const refreshAll = useCallback(async () => {
    try {
      const [
        list,
        dFC,
        tFC,
        rFC,
        paFC,
        hFC,
        crFC,
        shFC,
        alFC,
        ecoList,
      ] = await Promise.all([
        api.listDetections(),
        api.mapDetections(),
        api.mapTrajectories(),
        api.mapRiskZones(),
        api.mapProtectedAreas(),
        api.mapHabitats(),
        api.mapCoralReefs().catch(() => EMPTY_FC),
        api.mapSpeciesHabitats().catch(() => EMPTY_FC),
        api.mapAlertsGeoJSON().catch(() => EMPTY_FC),
        api.listEcologicalAlerts().catch(() => ({ total: 0, alerts: [] })),
      ]);

      setDetections(list.items);
      setDetectionsFC(dFC);
      setTrajectoriesFC(tFC);
      setRiskZonesFC(rFC);
      setProtectedAreasFC(paFC);
      setHabitatsFC(hFC);
      setCoralReefsFC(crFC);
      setSpeciesHabitatsFC(shFC);
      setAlertsFC(alFC);
      setEcologicalAlerts(ecoList.alerts);
      setLoadError(null);
    } catch (e: any) {
      setLoadError(
        e.message ||
          "Could not reach OceanGuard API. Is backend active on port 8000?"
      );
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Handle detection selection
  useEffect(() => {
    if (!selectedId) {
      setSelectedDetection(null);
      return;
    }
    api.getDetection(selectedId)
      .then((det) => {
        setSelectedDetection(det);
        setMapCenterCoords([det.longitude, det.latitude]);
      })
      .catch(() => setSelectedDetection(null));
  }, [selectedId]);

  function toggleLayer(key: string) {
    setVisibleLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  // Filtered detections FeatureCollection for Map
  const filteredDetectionsFC: FeatureCollection = {
    type: "FeatureCollection",
    features: detectionsFC.features.filter((f) => {
      const p = f.properties;
      if (filterMode === "actionable") return p.confidence >= 0.70;
      if (filterMode === "review") return p.confidence < 0.70 && p.incident_status === "unverified";
      if (filterMode === "assigned") return p.incident_status === "assigned" || p.incident_status === "being_handled";
      return true;
    }),
  };

  function handleSelectAlertFromTicker(externalId: string) {
    setSelectedId(externalId);
  }

  function handleOpenResponderForDetection(externalId: string) {
    setSelectedId(externalId);
    setIsResponderPortalOpen(true);
  }

  return (
    <main className={`relative h-screen w-screen overflow-hidden font-sans transition-colors ${
      theme === "light" ? "theme-light bg-slate-100 text-slate-800" : "bg-slate-950 text-slate-100"
    }`}>
      {/* 1. Full-screen Interactive Marine Map */}
      <div className="absolute inset-0">
        <MapView
          layers={{
            detections: filteredDetectionsFC,
            trajectories: trajectoriesFC,
            riskZones: riskZonesFC,
            protectedAreas: protectedAreasFC,
            habitats: habitatsFC,
            coralReefs: coralReefsFC,
            speciesHabitats: speciesHabitatsFC,
            ecologicalAlerts: alertsFC,
          }}
          onSelectDetection={setSelectedId}
          onSelectAlert={(alertId) => {
            const al = ecologicalAlerts.find((a) => a.id === alertId);
            if (al) setSelectedId(al.external_id);
          }}
          visibleLayers={visibleLayers}
          selectedDetectionId={selectedId}
          centerCoordinates={mapCenterCoords}
          chatOverlayFC={chatOverlayFC}
          theme={theme}
        />
      </div>

      {/* 2. Top-Left Branding & Layer Controller */}
      <div className="pointer-events-none absolute left-4 top-4 z-20 flex flex-col gap-3">
        <div className={`pointer-events-auto flex items-center justify-between gap-3 rounded-xl border px-4 py-2.5 shadow-xl backdrop-blur-md transition-colors ${
          theme === "light"
            ? "border-slate-200/90 bg-white/95 text-slate-800 shadow-slate-900/10"
            : "border-sky-500/25 bg-slate-950/90 text-slate-100 shadow-2xl"
        }`}>
          <div className="flex items-center gap-3">
            <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
              theme === "light" ? "bg-sky-100 text-sky-600" : "bg-sky-500/20 text-sky-400"
            }`}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className={`text-sm font-extrabold tracking-wide ${theme === "light" ? "text-slate-900" : "text-slate-100"}`}>OceanGuard AI</h1>
                <span className={`rounded px-1.5 py-0.2 text-[9px] font-bold ${
                  theme === "light" ? "bg-sky-100 text-sky-700" : "bg-sky-500/20 text-sky-300"
                }`}>
                  v2.0 PRO
                </span>
              </div>
              <div className={`text-[10px] tracking-wide ${theme === "light" ? "text-slate-500" : "text-slate-400"}`}>
                Marine Debris Intelligence &amp; Ecological Shield
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme Toggle Button */}
            <button
              id="theme-toggle-btn"
              onClick={toggleTheme}
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold transition ${
                theme === "light"
                  ? "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 shadow-sm"
                  : "border-sky-500/40 bg-sky-950/50 text-sky-300 hover:bg-sky-900/70"
              }`}
              title={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
            >
              <span>{theme === "light" ? "☀️ Light" : "🌙 Dark"}</span>
            </button>

            <button
              onClick={() => setIsResponderPortalOpen(true)}
              className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold transition ${
                theme === "light"
                  ? "border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 shadow-sm"
                  : "border-purple-500/40 bg-purple-950/50 text-purple-200 hover:bg-purple-900/70"
              }`}
              title="Open Responder & Admin Login Console"
            >
              <span>Admin / Login</span>
            </button>
          </div>
        </div>

        {/* Operational Filter Pills */}
        <div className={`pointer-events-auto flex gap-1 rounded-xl border p-1 shadow-lg backdrop-blur-md transition-colors ${
          theme === "light"
            ? "border-slate-200/90 bg-white/95 text-slate-700 shadow-slate-900/10"
            : "border-slate-800 bg-slate-950/90 text-slate-300"
        }`}>
          {[
            { id: "all", label: "All Debris" },
            { id: "actionable", label: "⚡ Actionable (≥70%)" },
            { id: "review", label: "🔍 Review (<70%)" },
            { id: "assigned", label: "🚢 Dispatched" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterMode(f.id as any)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                filterMode === f.id
                  ? "bg-sky-600 text-white shadow-sm"
                  : theme === "light"
                  ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <LayerToggle
          visibleLayers={visibleLayers}
          onToggle={toggleLayer}
          onOpenDataSources={() => setIsDataSourcesOpen(true)}
          theme={theme}
        />
      </div>

      {/* 3. Top-Center Alert Ticker */}
      <div className="pointer-events-none absolute left-1/2 top-4 z-20 flex -translate-x-1/2 flex-col items-center gap-2">
        <div className="pointer-events-auto w-full">
          <EcologicalAlertBanner
            alerts={ecologicalAlerts}
            onSelectAlert={handleSelectAlertFromTicker}
            onOpenResponderPortal={() => setIsResponderPortalOpen(true)}
            theme={theme}
          />
        </div>
      </div>

      {/* Error notification if backend is offline */}
      {loadError && (
        <div className="pointer-events-auto absolute left-1/2 top-28 z-30 -translate-x-1/2 rounded-xl border border-red-500/50 bg-red-950/95 px-4 py-2.5 text-xs text-red-200 shadow-2xl backdrop-blur">
          ⚠️ {loadError}
        </div>
      )}

      {/* 4. Right-side Marine Target Inspector Drawer */}
      <div className={`absolute right-0 top-0 z-20 h-full w-[410px] border-l shadow-2xl backdrop-blur-md transition-colors ${
        theme === "light"
          ? "border-slate-200/90 bg-white/98 text-slate-800"
          : "border-slate-800 bg-slate-950/95 text-slate-100"
      }`}>
        <DetectionPanel
          detection={selectedDetection}
          onAnalyzed={refreshAll}
          onOpenResponderWithDetection={handleOpenResponderForDetection}
          onClose={() => setSelectedId(null)}
          theme={theme}
        />
      </div>

      {/* 5. Bottom Map Legend */}
      <div className={`pointer-events-none absolute bottom-4 left-4 z-20 rounded-xl border px-3.5 py-2 text-[10px] shadow-xl backdrop-blur-md transition-colors ${
        theme === "light"
          ? "border-slate-200/90 bg-white/95 text-slate-700 shadow-slate-900/10"
          : "border-slate-800 bg-slate-950/90 text-slate-400"
      }`}>
        <div className={`mb-1 font-bold uppercase tracking-wider ${theme === "light" ? "text-slate-800" : "text-slate-300"}`}>Target Legend</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <LegendDot color="#ef4444" label="Awaiting Review (<70%)" theme={theme} />
          <LegendDot color="#f97316" label="Actionable Alert (≥70%)" theme={theme} />
          <LegendDot color="#10b981" label="Human Verified" theme={theme} />
          <LegendDot color="#f59e0b" label="Vessel Assigned" theme={theme} />
          <LegendDot color="#a855f7" label="Being Handled" theme={theme} />
          <LegendDot color="#38bdf8" label="Resolved / Recovered" theme={theme} />
        </div>
      </div>

      {/* 6. Responder & NGO Operations Modal */}
      <ResponderPortal
        isOpen={isResponderPortalOpen}
        onClose={() => setIsResponderPortalOpen(false)}
        onSelectDetectionOnMap={(extId) => {
          setSelectedId(extId);
          setIsResponderPortalOpen(false);
        }}
        onIncidentUpdated={refreshAll}
        theme={theme}
      />

      {/* 7. Data Sources & Autonomous Research Modal */}
      <DataSourcesModal
        isOpen={isDataSourcesOpen}
        onClose={() => setIsDataSourcesOpen(false)}
        theme={theme}
      />

      {/* 8. Vessel Debris Route Chatbot */}
      <ChatWidget
        onRouteDrawn={(fc) => setChatOverlayFC(fc)}
        theme={theme}
      />

      {/* Clear chat overlay button — shown only when a route is drawn */}
      {chatOverlayFC && (
        <button
          id="chat-clear-route-btn"
          onClick={() => setChatOverlayFC(null)}
          className={`
            fixed bottom-[6.5rem] right-[430px] z-40 flex items-center gap-1.5
            rounded-full border px-3 py-1.5 text-[11px] font-semibold shadow-lg backdrop-blur transition
            ${theme === "light"
              ? "border-sky-300 bg-white/95 text-sky-700 hover:bg-slate-50"
              : "border-sky-500/40 bg-slate-900/90 text-sky-300 hover:bg-slate-800"
            }
          `}
          title="Clear route overlay from map"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear Route
        </button>
      )}
    </main>
  );
}

function LegendDot({ color, label, theme = "light" }: { color: string; label: string; theme?: "light" | "dark" }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      <span className={theme === "light" ? "text-slate-700 font-medium" : "text-slate-300"}>{label}</span>
    </div>
  );
}
