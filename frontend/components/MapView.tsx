"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { ArcLayer, ScatterplotLayer, LineLayer } from "@deck.gl/layers";
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

// Generate realistic Indian Ocean Surface Current Vectors for deck.gl
function generateOceanCurrentVectors() {
  const vectors: Array<{ from: [number, number]; to: [number, number]; speed: number; region: string }> = [];

  // 1. Arabian Sea Southwest Monsoon Current (drifting northward/eastward along West Coast)
  for (let lat = 8.0; lat <= 21.0; lat += 1.2) {
    for (let lon = 68.0; lon <= 74.0; lon += 1.4) {
      const angle = 0.55 + Math.sin(lat * 0.4) * 0.15;
      const speed = 0.6 + Math.cos(lon * 0.2) * 0.25;
      vectors.push({
        from: [lon, lat],
        to: [lon + Math.cos(angle) * 0.85, lat + Math.sin(angle) * 0.85],
        speed,
        region: "Arabian Sea",
      });
    }
  }

  // 2. Bay of Bengal Cyclonic / East India Coastal Current (flowing northward along East Coast)
  for (let lat = 9.0; lat <= 20.0; lat += 1.3) {
    for (let lon = 81.0; lon <= 89.0; lon += 1.5) {
      const angle = 1.1 + Math.sin(lat * 0.3) * 0.2;
      const speed = 0.55 + Math.sin(lon * 0.3) * 0.2;
      vectors.push({
        from: [lon, lat],
        to: [lon + Math.cos(angle) * 0.8, lat + Math.sin(angle) * 0.85],
        speed,
        region: "Bay of Bengal",
      });
    }
  }

  // 3. Equatorial Gyre Current (westward flowing south of Sri Lanka / Maldives)
  for (let lat = 3.0; lat <= 6.5; lat += 1.1) {
    for (let lon = 70.0; lon <= 88.0; lon += 2.0) {
      vectors.push({
        from: [lon, lat],
        to: [lon - 1.1, lat + 0.05],
        speed: 0.85,
        region: "Equatorial Jet",
      });
    }
  }

  // 4. Lakshadweep & Maldives Channel Flow
  for (let lat = 7.5; lat <= 13.0; lat += 1.1) {
    vectors.push({
      from: [72.2, lat],
      to: [72.6, lat + 0.9],
      speed: 0.7,
      region: "Lakshadweep Passage",
    });
  }

  return vectors;
}

const STATIC_OCEAN_CURRENTS = generateOceanCurrentVectors();

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
  const deckOverlayRef = useRef<MapboxOverlay | null>(null);
  const loadedRef = useRef(false);
  const animFrameRef = useRef<number | null>(null);

  const [currentStyle, setCurrentStyle] = useState<keyof typeof BASEMAP_STYLES>("dark");
  const [showDeckCurrents, setShowDeckCurrents] = useState(true);
  const [showDeck3DDriftArcs, setShowDeck3DDriftArcs] = useState(true);
  const [driftForecastTimeHour, setDriftForecastTimeHour] = useState<number>(72);
  const [animTime, setAnimTime] = useState<number>(0);

  // Initialize MapLibre & deck.gl MapboxOverlay
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const styleUrl: any = BASEMAP_STYLES[currentStyle].url;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: [78.5, 14.5], // Centered on Indian Ocean & Subcontinent
      zoom: 4.8,
      pitch: 32, // 32 degree pitch to showcase 3D deck.gl arcs
      bearing: 0,
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ visualizePitch: true }), "top-right");

    // Initialize deck.gl MapboxOverlay
    const deckOverlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
    });
    deckOverlayRef.current = deckOverlay;
    map.addControl(deckOverlay as any);

    map.on("load", () => {
      loadedRef.current = true;
      setupMapLibreLayers(map, layers);
      updateDeckLayers();
    });

    // Start continuous particle animation loop
    let lastT = performance.now();
    const animate = (now: number) => {
      const dt = (now - lastT) / 1000;
      lastT = now;
      setAnimTime((prev) => (prev + dt * 0.4) % 1.0);
      animFrameRef.current = requestAnimationFrame(animate);
    };
    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
      deckOverlayRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update deck.gl layers when data, animation, or visibility changes
  useEffect(() => {
    updateDeckLayers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    layers,
    showDeckCurrents,
    showDeck3DDriftArcs,
    driftForecastTimeHour,
    animTime,
    selectedDetectionId,
  ]);

  function updateDeckLayers() {
    if (!deckOverlayRef.current) return;

    const deckLayers: any[] = [];

    // 1. Deck.gl Animated Ocean Current Flow Vectors
    if (showDeckCurrents) {
      // Calculate dynamic pulse offset
      const currentLines = STATIC_OCEAN_CURRENTS.map((c, i) => {
        const offset = ((animTime + i * 0.05) % 1.0);
        // Interpolate flowing particle head
        const pLon = c.from[0] + (c.to[0] - c.from[0]) * offset;
        const pLat = c.from[1] + (c.to[1] - c.from[1]) * offset;
        return {
          ...c,
          head: [pLon, pLat],
        };
      });

      // Flow background streamlines
      deckLayers.push(
        new LineLayer({
          id: "deck-ocean-current-lines",
          data: currentLines,
          getSourcePosition: (d: any) => d.from,
          getTargetPosition: (d: any) => d.to,
          getColor: [6, 182, 212, 60], // subtle translucent cyan
          getWidth: 1.5,
          widthUnits: "pixels",
          pickable: false,
        })
      );

      // Flow moving glowing particle heads
      deckLayers.push(
        new ScatterplotLayer({
          id: "deck-ocean-current-particles",
          data: currentLines,
          getPosition: (d: any) => d.head,
          getRadius: 38000,
          getFillColor: [34, 211, 238, 200], // neon cyan glow
          stroked: false,
          pickable: false,
        })
      );
    }

    // 2. Deck.gl 3D Elevated Parabolic Drift Arcs
    if (showDeck3DDriftArcs && layers.trajectories) {
      const arcData: any[] = [];

      // Extract trajectories grouped by detection
      const detCoordsMap = new Map<string, [number, number]>();
      layers.detections.features.forEach((f) => {
        detCoordsMap.set(f.properties.external_id, f.geometry.coordinates as [number, number]);
      });

      layers.trajectories.features.forEach((f) => {
        if (f.geometry.type === "LineString" && f.geometry.coordinates.length >= 2) {
          const detId = f.properties.detection_id;
          const forecastHour = f.properties.forecast_hour;

          // Only show up to current scrubber hour
          if (forecastHour <= driftForecastTimeHour) {
            const start = f.geometry.coordinates[0];
            const end = f.geometry.coordinates[1];
            const isSelected = detId === selectedDetectionId;

            arcData.push({
              id: `${detId}-${forecastHour}`,
              source: start,
              target: end,
              detId,
              forecastHour,
              isSelected,
            });
          }
        }
      });

      deckLayers.push(
        new ArcLayer({
          id: "deck-3d-drift-arcs",
          data: arcData,
          getSourcePosition: (d: any) => d.source,
          getTargetPosition: (d: any) => d.target,
          getSourceColor: (d: any) => (d.isSelected ? [249, 115, 22, 255] : [245, 158, 11, 200]), // amber origin
          getTargetColor: (d: any) => (d.isSelected ? [14, 165, 233, 255] : [56, 189, 248, 220]), // sky blue destination
          getWidth: (d: any) => (d.isSelected ? 5 : 2.5),
          getHeight: 0.8, // 3D parabolic elevation factor
          pickable: true,
          onClick: (info: any) => {
            if (info.object?.detId) {
              onSelectDetection(info.object.detId);
            }
          },
        })
      );
    }

    // 3. Deck.gl Glowing 3D Scatterplot Beacons on Detections
    const detectionPoints = layers.detections.features.map((f) => ({
      coordinates: f.geometry.coordinates,
      external_id: f.properties.external_id,
      confidence: f.properties.confidence,
      status: f.properties.incident_status || f.properties.status,
      isSelected: f.properties.external_id === selectedDetectionId,
    }));

    deckLayers.push(
      new ScatterplotLayer({
        id: "deck-detection-glow-beacons",
        data: detectionPoints,
        getPosition: (d: any) => d.coordinates,
        getRadius: (d: any) => (d.isSelected ? 55000 : 32000),
        getFillColor: (d: any) => {
          if (d.status === "resolved") return [56, 189, 248, 160];
          if (d.confidence >= 0.70) return [249, 115, 22, 190]; // high confidence orange
          return [239, 68, 68, 170]; // review red
        },
        stroked: true,
        getLineColor: [255, 255, 255, 220],
        getLineWidth: 2,
        lineWidthUnits: "pixels",
        pickable: true,
        onClick: (info: any) => {
          if (info.object?.external_id) {
            onSelectDetection(info.object.external_id);
          }
        },
      })
    );

    deckOverlayRef.current.setProps({
      layers: deckLayers,
    });
  }

  // Handle Style Switching
  function switchBasemap(styleKey: keyof typeof BASEMAP_STYLES) {
    if (!mapRef.current || styleKey === currentStyle) return;
    setCurrentStyle(styleKey);
    const styleUrl: any = BASEMAP_STYLES[styleKey].url;
    mapRef.current.setStyle(styleUrl);
    mapRef.current.once("style.load", () => {
      if (mapRef.current) {
        setupMapLibreLayers(mapRef.current, layers);
        updateDeckLayers();
      }
    });
  }

  // Setup all base MapLibre vector layers
  function setupMapLibreLayers(map: MapLibreMap, currentLayers: MapLayers) {
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
          "fill-opacity": 0.24,
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
          "fill-opacity": 0.16,
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

    // 4. Drift Trajectory Uncertainty Cones
    if (!map.getSource("trajectories")) {
      map.addSource("trajectories", {
        type: "geojson",
        data: (currentLayers.trajectories || { type: "FeatureCollection", features: [] }) as any,
      });
      map.addLayer({
        id: "uncertainty-fill",
        type: "fill",
        source: "trajectories",
        filter: ["==", ["get", "layer"], "uncertainty_polygon"],
        paint: {
          "fill-color": "#facc15",
          "fill-opacity": 0.12,
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

    // 7. Base Detections with status colors
    if (!map.getSource("detections")) {
      map.addSource("detections", {
        type: "geojson",
        data: (currentLayers.detections || { type: "FeatureCollection", features: [] }) as any,
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
               ${props.is_actionable_alert ? `<div style="margin-top:6px;font-size:10px;color:#f97316;font-weight:600">⚡ Actionable Cleanup Priority (≥70%)</div>` : `<div style="margin-top:6px;font-size:10px;color:#94a3b8">⚠️ Low-Confidence: Awaiting Human Verification</div>`}
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
      zoom: 7.8,
      pitch: 45,
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
    setVis("risk-zones-fill", visibleLayers.riskZones);
    setVis("risk-zones-line", visibleLayers.riskZones);
    setVis("ecological-alerts-glow", visibleLayers.ecologicalAlerts ?? true);
    setVis("ecological-alerts-points", visibleLayers.ecologicalAlerts ?? true);
    setVis("detections-circles", visibleLayers.detections ?? true);
  }, [visibleLayers]);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div ref={containerRef} className="h-full w-full" />

      {/* Floating Tactical Deck.gl & Time-Scrubber Control Toolbar (Bottom-Center) */}
      <div className="pointer-events-auto absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 rounded-2xl border border-sky-500/25 bg-slate-950/90 px-4 py-2.5 shadow-2xl backdrop-blur-md">
        {/* Ocean Current Flow Toggle */}
        <button
          onClick={() => setShowDeckCurrents((prev) => !prev)}
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
            showDeckCurrents
              ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20"
              : "text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
          title="Toggle WebGL Animated Ocean Current Particle Streamlines"
        >
          <span className={showDeckCurrents ? "animate-pulse" : ""}>🌊</span>
          <span>Ocean Current Flow</span>
        </button>

        {/* 3D Drift Arcs Toggle */}
        <button
          onClick={() => setShowDeck3DDriftArcs((prev) => !prev)}
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
            showDeck3DDriftArcs
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/20"
              : "text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
          title="Toggle 3D Elevated Parabolic Drift Arcs"
        >
          <span>⚡</span>
          <span>3D Drift Arcs</span>
        </button>

        <div className="h-5 w-px bg-slate-800" />

        {/* 72-Hour Forecast Time Scrubber Slider */}
        <div className="flex items-center gap-2.5 text-xs text-slate-300">
          <span className="font-semibold text-[11px] text-slate-400 whitespace-nowrap">
            Drift Forecast: <strong className="text-sky-400">+{driftForecastTimeHour}h</strong>
          </span>
          <input
            type="range"
            min="0"
            max="72"
            step="24"
            value={driftForecastTimeHour}
            onChange={(e) => setDriftForecastTimeHour(Number(e.target.value))}
            className="w-24 accent-sky-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
          />
          <div className="flex gap-1 text-[9px] font-bold text-slate-400">
            {[0, 24, 48, 72].map((h) => (
              <button
                key={h}
                onClick={() => setDriftForecastTimeHour(h)}
                className={`rounded px-1.5 py-0.5 ${
                  driftForecastTimeHour === h ? "bg-sky-500 text-white" : "hover:text-slate-200"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Basemap Switcher Control in bottom-right */}
      <div className="absolute bottom-6 right-4 z-10 flex items-center rounded-xl border border-sky-950 bg-slate-900/90 p-1 shadow-xl backdrop-blur">
        {(["dark", "satellite", "light"] as const).map((key) => (
          <button
            key={key}
            onClick={() => switchBasemap(key)}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
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
