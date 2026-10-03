"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "@/types";

export interface MapLayers {
  detections: FeatureCollection;
  trajectories: FeatureCollection | null;
  riskZones: FeatureCollection | null;
  protectedAreas: FeatureCollection;
  habitats: FeatureCollection;
  coralReefs?: FeatureCollection | null;
  speciesHabitats?: FeatureCollection | null;
  ecologicalAlerts?: FeatureCollection | null;
}

export const BASEMAP_STYLES = {
  dark: {
    name: "Tactical Dark",
    url: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  },
  satellite: {
    name: "Ocean Satellite",
    url: {
      version: 8,
      sources: {
        "esri-satellite": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "Esri, Maxar, Earthstar Geographics",
        },
      },
      layers: [
        {
          id: "esri-satellite-layer",
          type: "raster",
          source: "esri-satellite",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
    },
  },
  light: {
    name: "Positron Light",
    url: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  },
};

interface MapViewProps {
  layers: MapLayers;
  onSelectDetection: (externalId: string) => void;
  onSelectAlert?: (alertId: string) => void;
  visibleLayers: Record<string, boolean>;
  selectedDetectionId?: string | null;
  centerCoordinates?: [number, number] | null;
}

export default function MapView({
  layers,
  onSelectDetection,
  onSelectAlert,
  visibleLayers,
  selectedDetectionId,
  centerCoordinates,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const loadedRef = useRef(false);
  const [currentStyle, setCurrentStyle] = useState<keyof typeof BASEMAP_STYLES>("dark");

  // Initialize Map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const styleUrl: any = BASEMAP_STYLES[currentStyle].url;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: [78.5, 14.5], // Centered on Indian Ocean & Subcontinent
      zoom: 4.8,
      pitch: 15,
      bearing: 0,
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ visualizePitch: true }), "top-right");

    map.on("load", () => {
      loadedRef.current = true;
      setupMapLayers(map, layers);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle Style Switching
  function switchBasemap(styleKey: keyof typeof BASEMAP_STYLES) {
    if (!mapRef.current || styleKey === currentStyle) return;
    setCurrentStyle(styleKey);
    const styleUrl: any = BASEMAP_STYLES[styleKey].url;
    mapRef.current.setStyle(styleUrl);
    mapRef.current.once("style.load", () => {
      if (mapRef.current) {
        setupMapLayers(mapRef.current, layers);
      }
    });
  }

  // Setup all layers
  function setupMapLayers(map: MapLibreMap, currentLayers: MapLayers) {
    // 1. Protected Areas (WDPA)
    if (!map.getSource("protected-areas")) {
      map.addSource("protected-areas", {
        type: "geojson",
        data: (currentLayers.protectedAreas || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "protected-areas-fill",
        type: "fill",
        source: "protected-areas",
        paint: {
          "fill-color": "#10b981",
          "fill-opacity": 0.16,
        },
      });
      map.addLayer({
        id: "protected-areas-line",
        type: "line",
        source: "protected-areas",
        paint: {
          "line-color": "#10b981",
          "line-width": 1.6,
          "line-dasharray": [3, 2],
        },
      });
    }

    // 2. Coral Reefs (GCRMN / UNEP-WCMC)
    if (!map.getSource("coral-reefs")) {
      map.addSource("coral-reefs", {
        type: "geojson",
        data: (currentLayers.coralReefs || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "coral-reefs-fill",
        type: "fill",
        source: "coral-reefs",
        paint: {
          "fill-color": "#06b6d4",
          "fill-opacity": 0.22,
        },
      });
      map.addLayer({
        id: "coral-reefs-line",
        type: "line",
        source: "coral-reefs",
        paint: {
          "line-color": "#22d3ee",
          "line-width": 1.8,
        },
      });
    }

    // 3. Species & Habitats (SWOT / OBIS-SEAMAP)
    if (!map.getSource("species-habitats")) {
      map.addSource("species-habitats", {
        type: "geojson",
        data: (currentLayers.speciesHabitats || currentLayers.habitats || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "species-habitats-fill",
        type: "fill",
        source: "species-habitats",
        paint: {
          "fill-color": "#a855f7",
          "fill-opacity": 0.15,
        },
      });
      map.addLayer({
        id: "species-habitats-line",
        type: "line",
        source: "species-habitats",
        paint: {
          "line-color": "#c084fc",
          "line-width": 1.4,
          "line-dasharray": [2, 2],
        },
      });
    }

    // 4. Drift Trajectories & Uncertainty Cones
    if (!map.getSource("trajectories")) {
      map.addSource("trajectories", {
        type: "geojson",
        data: (currentLayers.trajectories || { type: "FeatureCollection", features: [] }) as any,
      });
      // Uncertainty polygon cone
      map.addLayer({
        id: "uncertainty-fill",
        type: "fill",
        source: "trajectories",
        filter: ["==", ["get", "layer"], "uncertainty_polygon"],
        paint: {
          "fill-color": "#facc15",
          "fill-opacity": 0.14,
        },
      });
      map.addLayer({
        id: "uncertainty-stroke",
        type: "line",
        source: "trajectories",
        filter: ["==", ["get", "layer"], "uncertainty_polygon"],
        paint: {
          "line-color": "#eab308",
          "line-width": 1.2,
          "line-dasharray": [4, 3],
        },
      });
      // Trajectory vector paths
      map.addLayer({
        id: "trajectory-lines",
        type: "line",
        source: "trajectories",
        filter: ["in", ["get", "layer"], ["literal", ["trajectory_24h", "trajectory_48h", "trajectory_72h"]]],
        paint: {
          "line-color": "#38bdf8",
          "line-width": 2.2,
          "line-dasharray": [2, 2],
        },
      });
    }

    // 5. High-Risk Zones
    if (!map.getSource("risk-zones")) {
      map.addSource("risk-zones", {
        type: "geojson",
        data: (currentLayers.riskZones || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "risk-zones-fill",
        type: "fill",
        source: "risk-zones",
        paint: {
          "fill-color": [
            "match",
            ["get", "risk_level"],
            "CRITICAL", "#ef4444",
            "HIGH", "#f97316",
            "#eab308",
          ],
          "fill-opacity": 0.28,
        },
      });
      map.addLayer({
        id: "risk-zones-line",
        type: "line",
        source: "risk-zones",
        paint: {
          "line-color": [
            "match",
            ["get", "risk_level"],
            "CRITICAL", "#f87171",
            "HIGH", "#fb923c",
            "#facc15",
          ],
          "line-width": 1.5,
        },
      });
    }

    // 6. Ecological Threat Alert Impact Points
    if (!map.getSource("ecological-alerts")) {
      map.addSource("ecological-alerts", {
        type: "geojson",
        data: (currentLayers.ecologicalAlerts || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "ecological-alerts-glow",
        type: "circle",
        source: "ecological-alerts",
        paint: {
          "circle-radius": 14,
          "circle-color": [
            "match",
            ["get", "severity"],
            "CRITICAL", "#ef4444",
            "HIGH", "#f97316",
            "#38bdf8",
          ],
          "circle-opacity": 0.25,
        },
      });
      map.addLayer({
        id: "ecological-alerts-points",
        type: "circle",
        source: "ecological-alerts",
        paint: {
          "circle-radius": 7,
          "circle-color": [
            "match",
            ["get", "severity"],
            "CRITICAL", "#dc2626",
            "HIGH", "#ea580c",
            "#0284c7",
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
        },
      });

      map.on("click", "ecological-alerts-points", (e) => {
        const feature = e.features?.[0];
        if (!feature) return;
        const p = feature.properties as any;
        if (onSelectAlert && p.id) {
          onSelectAlert(p.id);
        }
        new maplibregl.Popup({ closeButton: true })
          .setLngLat((feature.geometry as any).coordinates)
          .setHTML(
            `<div class="p-1 space-y-1">
               <div class="text-[10px] font-bold uppercase tracking-wider text-rose-400">
                 ⚠️ ECOLOGICAL THREAT [${p.severity}]
               </div>
               <div class="text-xs font-semibold text-slate-100">${p.headline || p.region_name}</div>
               <div class="text-[11px] text-slate-300">Target Area: <strong>${p.region_name}</strong></div>
               <div class="text-[11px] text-slate-300">Distance: <strong>${Number(p.distance_km).toFixed(1)} km</strong></div>
               <div class="text-[10px] text-slate-400 italic">Drift Arrival: ~${Number(p.estimated_impact_hours).toFixed(1)} hours</div>
             </div>`
          )
          .addTo(map);
      });
    }

    // 7. Detections
    if (!map.getSource("detections")) {
      map.addSource("detections", {
        type: "geojson",
        data: (currentLayers.detections || { type: "FeatureCollection", features: [] }) as any,
      });

      // Outer halo for high confidence detections
      map.addLayer({
        id: "detections-halo",
        type: "circle",
        source: "detections",
        filter: [">=", ["get", "confidence"], 0.7],
        paint: {
          "circle-radius": 15,
          "circle-color": "#f97316",
          "circle-opacity": 0.22,
        },
      });

      map.addLayer({
        id: "detections-circles",
        type: "circle",
        source: "detections",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            4, 7,
            8, 12,
            12, 16,
          ],
          "circle-color": [
            "match",
            ["get", "incident_status"],
            "resolved", "#38bdf8",     // blue
            "being_handled", "#a855f7", // purple
            "assigned", "#f59e0b",      // amber
            "verified", "#10b981",      // green
            "rejected", "#64748b",      // slate
            "#ef4444",                  // red - unverified
          ],
          "circle-stroke-width": 2.5,
          "circle-stroke-color": "#091224",
        },
      });

      map.on("click", "detections-circles", (e) => {
        const feature = e.features?.[0];
        if (!feature) return;
        const props = feature.properties as any;
        onSelectDetection(props.external_id);

        const statusColors: Record<string, string> = {
          unverified: "#ef4444",
          verified: "#10b981",
          assigned: "#f59e0b",
          being_handled: "#a855f7",
          resolved: "#38bdf8",
        };
        const statusColor = statusColors[props.incident_status || props.status] || "#ef4444";

        new maplibregl.Popup({ closeButton: true })
          .setLngLat((feature.geometry as any).coordinates)
          .setHTML(
            `<div style="font-size:12px;line-height:1.45;min-width:180px">
               <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                 <strong style="color:#f8fafc;font-size:13px">${props.external_id}</strong>
                 <span style="background:${statusColor}22;color:${statusColor};border:1px solid ${statusColor}66;border-radius:4px;padding:2px 6px;font-size:9px;font-weight:700;text-transform:uppercase">
                   ${props.incident_status || props.status}
                 </span>
               </div>
               <div style="color:#94a3b8;margin-bottom:4px">${String(props.object_class).replaceAll("_", " ")}</div>
               <div style="display:flex;justify-content:space-between;font-size:11px;color:#cbd5e1;margin-bottom:2px">
                 <span>Confidence:</span>
                 <strong style="color:${props.confidence >= 0.7 ? '#34d399' : '#f87171'}">
                   ${(props.confidence * 100).toFixed(1)}%
                 </strong>
               </div>
               ${props.assigned_team ? `<div style="font-size:11px;color:#cbd5e1">Team: <strong>${props.assigned_team}</strong></div>` : ""}
               ${props.is_actionable_alert ? `<div style="margin-top:6px;font-size:10px;color:#f97316;font-weight:600">⚡ Actionable Cleanup Priority (>70%)</div>` : `<div style="margin-top:6px;font-size:10px;color:#94a3b8">⚠️ Low-Confidence: Awaiting Human Verification</div>`}
             </div>`
          )
          .addTo(map);
      });

      map.on("mouseenter", "detections-circles", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "detections-circles", () => (map.getCanvas().style.cursor = ""));
      map.on("mouseenter", "ecological-alerts-points", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "ecological-alerts-points", () => (map.getCanvas().style.cursor = ""));
    }
  }

  // Update GeoJSON data when layers change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;

    (map.getSource("detections") as maplibregl.GeoJSONSource)?.setData(layers.detections as any);
    (map.getSource("protected-areas") as maplibregl.GeoJSONSource)?.setData(layers.protectedAreas as any);
    (map.getSource("species-habitats") as maplibregl.GeoJSONSource)?.setData(
      (layers.speciesHabitats || layers.habitats) as any
    );
    if (layers.coralReefs) {
      (map.getSource("coral-reefs") as maplibregl.GeoJSONSource)?.setData(layers.coralReefs as any);
    }
    if (layers.trajectories) {
      (map.getSource("trajectories") as maplibregl.GeoJSONSource)?.setData(layers.trajectories as any);
    }
    if (layers.riskZones) {
      (map.getSource("risk-zones") as maplibregl.GeoJSONSource)?.setData(layers.riskZones as any);
    }
    if (layers.ecologicalAlerts) {
      (map.getSource("ecological-alerts") as maplibregl.GeoJSONSource)?.setData(layers.ecologicalAlerts as any);
    }
  }, [layers]);

  // Center/Fly to coordinate if specified
  useEffect(() => {
    if (!mapRef.current || !centerCoordinates) return;
    mapRef.current.flyTo({
      center: centerCoordinates,
      zoom: 7.5,
      essential: true,
      speed: 1.2,
    });
  }, [centerCoordinates]);

  // Layer Visibility toggles
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;

    const setVis = (layerId: string, visible: boolean) => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
      }
    };

    setVis("protected-areas-fill", visibleLayers.protectedAreas);
    setVis("protected-areas-line", visibleLayers.protectedAreas);
    setVis("coral-reefs-fill", visibleLayers.coralReefs ?? true);
    setVis("coral-reefs-line", visibleLayers.coralReefs ?? true);
    setVis("species-habitats-fill", visibleLayers.speciesHabitats ?? true);
    setVis("species-habitats-line", visibleLayers.speciesHabitats ?? true);
    setVis("uncertainty-fill", visibleLayers.trajectories);
    setVis("uncertainty-stroke", visibleLayers.trajectories);
    setVis("trajectory-lines", visibleLayers.trajectories);
    setVis("risk-zones-fill", visibleLayers.riskZones);
    setVis("risk-zones-line", visibleLayers.riskZones);
    setVis("ecological-alerts-glow", visibleLayers.ecologicalAlerts ?? true);
    setVis("ecological-alerts-points", visibleLayers.ecologicalAlerts ?? true);
    setVis("detections-halo", visibleLayers.detections ?? true);
    setVis("detections-circles", visibleLayers.detections ?? true);
  }, [visibleLayers]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {/* Basemap Switcher Control in bottom-right */}
      <div className="absolute bottom-6 right-4 z-10 flex items-center rounded-lg border border-sky-950 bg-slate-900/90 p-1 shadow-xl backdrop-blur">
        {(["dark", "satellite", "light"] as const).map((key) => (
          <button
            key={key}
            onClick={() => switchBasemap(key)}
            className={`rounded px-2.5 py-1 text-[11px] font-medium transition ${
              currentStyle === key
                ? "bg-sky-500 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {BASEMAP_STYLES[key].name}
          </button>
        ))}
      </div>
    </div>
  );
}
