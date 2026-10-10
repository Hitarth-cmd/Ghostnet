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
import ModelInferenceModal from "@/components/ModelInferenceModal";

// Dynamic import for MapLibre
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const EMPTY_FC: FeatureCollection = { type: "FeatureCollection", features: [] };

const HOTSPOT_REGIONS = [
  { id: "goa", name: "Goa Waters", lat: 15.20, lon: 72.85 },
  { id: "mumbai", name: "Mumbai Port", lat: 18.80, lon: 72.15 },
  { id: "mannar", name: "Gulf of Mannar", lat: 8.85, lon: 79.45 },
  { id: "lakshadweep", name: "Lakshadweep", lat: 10.55, lon: 72.45 },
  { id: "andaman", name: "Andaman Sea", lat: 11.60, lon: 93.15 },
  { id: "kochi", name: "Kochi Waters", lat: 9.80, lon: 75.60 },
  { id: "chennai", name: "Chennai Coast", lat: 13.15, lon: 80.40 },
  { id: "kutch", name: "Gulf of Kutch", lat: 22.50, lon: 69.20 },
];

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

  // Live Earth Engine scanning states
  const [isScanningGEE, setIsScanningGEE] = useState(false);
  const [geeScanStep, setGeeScanStep] = useState<string | null>(null);
  const [selectedHotspot, setSelectedHotspot] = useState(HOTSPOT_REGIONS[0]);

  // Modals
  const [isResponderPortalOpen, setIsResponderPortalOpen] = useState(false);
  const [isDataSourcesOpen, setIsDataSourcesOpen] = useState(false);
  const [isModelInferenceOpen, setIsModelInferenceOpen] = useState(false);

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

  async function handleTriggerGEEScan(region = selectedHotspot) {
    setIsScanningGEE(true);
    setGeeScanStep(`Ingesting Sentinel-2 imagery for ${region.name} from Earth Engine (balmy-ocean-509105-v8)...`);
    try {
      await new Promise((r) => setTimeout(r, 600));
      setGeeScanStep(`Running ViT-UNet++ model inference (segmentation_best.pth) on multispectral bands...`);

      const scanRes = await api.scanEarthEngine({
        latitude: region.lat,
        longitude: region.lon,
        pixel_size_meters: 10.0,
        plot_to_map: true,
      });

      const areaM2 = scanRes.summary?.debris_area_m2 || 0;
      setGeeScanStep(`Marine debris identified (${areaM2.toLocaleString()} m²)! Plotting to map...`);
      await refreshAll();

      if (scanRes.created_detections && scanRes.created_detections.length > 0) {
        const newExtId = scanRes.created_detections[0].external_id;
        setSelectedId(newExtId);
        setMapCenterCoords([region.lon, region.lat]);
      } else {
        setMapCenterCoords([region.lon, region.lat]);
      }

      await new Promise((r) => setTimeout(r, 1200));
      setGeeScanStep(null);
    } catch (e: any) {
      setGeeScanStep(null);
      setLoadError(e.message || "Failed to scan Sentinel-2 satellite imagery from Earth Engine");
    } finally {
      setIsScanningGEE(false);
    }
  }

  async function handleSyncAllCatalog() {
    setIsScanningGEE(true);
    setGeeScanStep("Synchronizing Sentinel-2 observations across Indian coastal waters from Earth Engine (balmy-ocean-509105-v8)...");
    try {
      const res = await api.syncEarthEngineCatalog();
      setGeeScanStep(`Successfully updated ${res.active_detections} Sentinel-2 marine debris targets!`);
      await refreshAll();
      await new Promise((r) => setTimeout(r, 1500));
      setGeeScanStep(null);
    } catch (e: any) {
      setGeeScanStep(null);
      setLoadError(e.message || "Failed to sync Earth Engine satellite catalog");
    } finally {
      setIsScanningGEE(false);
    }
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* Live Earth Engine Scanning Notification */}
      {geeScanStep && (
        <div className="pointer-events-auto fixed top-6 left-1/2 z-50 -translate-x-1/2 rounded-2xl border border-sky-400/60 bg-slate-950/95 px-6 py-3.5 shadow-2xl backdrop-blur-md flex items-center gap-3.5 animate-pulse">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
          <div>
            <div className="text-[11px] font-bold text-sky-300 flex items-center gap-2">
              <span>Google Earth Engine Pipeline</span>
              <span className="rounded bg-sky-500/20 px-1.5 py-0.5 text-[9px] font-mono text-sky-200">
                balmy-ocean-509105-v8
              </span>
            </div>
            <div className="text-xs text-slate-100 font-semibold mt-0.5">
              {geeScanStep}
            </div>
          </div>
        </div>
      )}

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
        />
      </div>

      {/* 2. Top-Left Branding & Layer Controller */}
      <div className="pointer-events-none absolute left-4 top-4 z-20 flex flex-col gap-3">
        <div className="pointer-events-auto flex items-center justify-between gap-3 rounded-xl border border-sky-500/25 bg-slate-950/90 px-4 py-2.5 shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-extrabold tracking-wide text-slate-100">OceanGuard AI</h1>
                <span className="rounded bg-sky-500/20 px-1.5 py-0.2 text-[9px] font-bold text-sky-300">
                  v2.0 PRO
                </span>
              </div>
              <div className="text-[10px] tracking-wide text-slate-400">
                Marine Debris Intelligence &amp; Ecological Shield
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsModelInferenceOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-sky-500/40 bg-sky-950/70 px-2.5 py-1.5 text-[11px] font-bold text-sky-200 transition hover:bg-sky-900/80 shadow-sm"
              title="Scan Satellite Imagery with trained ViT-UNet++ AI Model (segmentation_best.pth)"
            >
              <span>🛰️</span>
              <span>AI Model Scanner</span>
            </button>

            <button
              onClick={() => setIsResponderPortalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-950/50 px-2.5 py-1.5 text-[11px] font-bold text-purple-200 transition hover:bg-purple-900/70"
              title="Open Responder & Admin Login Console"
            >
              <span>👑</span>
              <span>Admin / Login</span>
            </button>
          </div>
        </div>

        {/* Live Earth Engine Satellite Ingestion Toolbar */}
        <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-sky-500/40 bg-slate-950/95 px-3 py-2 shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-sky-300">
              GEE Ingest
            </span>
          </div>

          <select
            value={selectedHotspot.id}
            onChange={(e) => {
              const f = HOTSPOT_REGIONS.find((r) => r.id === e.target.value);
              if (f) setSelectedHotspot(f);
            }}
            className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] font-semibold text-slate-200 outline-none cursor-pointer"
            disabled={isScanningGEE}
          >
            {HOTSPOT_REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.lat.toFixed(1)}°N, {r.lon.toFixed(1)}°E)
              </option>
            ))}
          </select>

          <button
            onClick={() => handleTriggerGEEScan()}
            disabled={isScanningGEE}
            className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-2.5 py-1 text-[11px] font-bold text-white shadow transition hover:bg-sky-500 disabled:opacity-50"
            title="Fetch live Sentinel-2 satellite image from Earth Engine for this location and run marine debris inference"
          >
            {isScanningGEE ? (
              <>
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <span>🛰️</span>
                <span>Fetch Satellite &amp; Run Model</span>
              </>
            )}
          </button>

          <button
            onClick={handleSyncAllCatalog}
            disabled={isScanningGEE}
            className="rounded-lg border border-sky-500/30 bg-sky-950/50 px-2 py-1 text-[10px] font-semibold text-sky-200 hover:bg-sky-900/60 disabled:opacity-50"
            title="Ingest Sentinel-2 data across all 8 Indian coastal regions via Earth Engine balmy-ocean-509105-v8"
          >
            Sync All
          </button>
        </div>

        {/* Operational Filter Pills */}
        <div className="pointer-events-auto flex gap-1 rounded-xl border border-slate-800 bg-slate-950/90 p-1 shadow-lg backdrop-blur-md">
          {[
            { id: "all", label: "All Debris" },
            { id: "actionable", label: "⚡ Actionable (&ge;70%)" },
            { id: "review", label: "🔍 Review (&lt;70%)" },
            { id: "assigned", label: "🚢 Dispatched" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterMode(f.id as any)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                filterMode === f.id
                  ? "bg-sky-600 text-white shadow-sm"
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
        />
      </div>

      {/* 3. Top-Center Alert Ticker */}
      <div className="pointer-events-none absolute left-1/2 top-4 z-20 flex -translate-x-1/2 flex-col items-center gap-2">
        <div className="pointer-events-auto w-full">
          <EcologicalAlertBanner
            alerts={ecologicalAlerts}
            onSelectAlert={handleSelectAlertFromTicker}
            onOpenResponderPortal={() => setIsResponderPortalOpen(true)}
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
      <div className="absolute right-0 top-0 z-20 h-full w-[410px] border-l border-slate-800 bg-slate-950/95 shadow-2xl backdrop-blur-md">
        <DetectionPanel
          detection={selectedDetection}
          onAnalyzed={refreshAll}
          onOpenResponderWithDetection={handleOpenResponderForDetection}
          onClose={() => setSelectedId(null)}
        />
      </div>

      {/* 5. Bottom Map Legend */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-20 rounded-xl border border-slate-800 bg-slate-950/90 px-3.5 py-2 text-[10px] text-slate-400 shadow-xl backdrop-blur-md">
        <div className="mb-1 font-bold uppercase tracking-wider text-slate-300">Target Legend</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <LegendDot color="#ef4444" label="Awaiting Review (<70%)" />
          <LegendDot color="#f97316" label="Actionable Alert (≥70%)" />
          <LegendDot color="#10b981" label="Human Verified" />
          <LegendDot color="#f59e0b" label="Vessel Assigned" />
          <LegendDot color="#a855f7" label="Being Handled" />
          <LegendDot color="#38bdf8" label="Resolved / Recovered" />
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
      />

      {/* 7. Data Sources & Autonomous Research Modal */}
      <DataSourcesModal
        isOpen={isDataSourcesOpen}
        onClose={() => setIsDataSourcesOpen(false)}
      />

      {/* 8. AI Model Scanner Modal */}
      <ModelInferenceModal
        isOpen={isModelInferenceOpen}
        onClose={() => setIsModelInferenceOpen(false)}
        onDetectionPlotted={refreshAll}
      />

      {/* 9. Vessel Debris Route Chatbot */}
      <ChatWidget
        onRouteDrawn={(fc) => setChatOverlayFC(fc)}
      />

      {/* Clear chat overlay button — shown only when a route is drawn */}
      {chatOverlayFC && (
        <button
          id="chat-clear-route-btn"
          onClick={() => setChatOverlayFC(null)}
          className="
            fixed bottom-[6.5rem] right-[430px] z-40 flex items-center gap-1.5
            rounded-full border border-sky-500/40 bg-slate-900/90 px-3 py-1.5
            text-[11px] font-semibold text-sky-300 shadow-lg backdrop-blur
            transition hover:bg-slate-800
          "
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

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      <span className="text-slate-300">{label}</span>
    </div>
  );
}
