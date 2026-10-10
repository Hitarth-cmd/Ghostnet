"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, NavigationControl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { ArcLayer, ScatterplotLayer, LineLayer, PathLayer, PolygonLayer } from "@deck.gl/layers";
import type { FeatureCollection } from "@/types";
import { api } from "@/lib/api";

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
  light: {
    name: "Voyager Marine",
    url: "/map-styles/voyager-marine.json",
  },
  ocean: {
    name: "Ocean Bathymetry",
    url: {
      version: 8,
      sources: {
        "esri-ocean": {
          type: "raster",
          tiles: [
            "https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "Esri, GEBCO, NOAA, National Geographic",
        },
        "esri-ocean-ref": {
          type: "raster",
          tiles: [
            "https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
        },
      },
      layers: [
        {
          id: "esri-ocean-layer",
          type: "raster",
          source: "esri-ocean",
          minzoom: 0,
          maxzoom: 19,
        },
        {
          id: "esri-ocean-ref-layer",
          type: "raster",
          source: "esri-ocean-ref",
          minzoom: 0,
          maxzoom: 19,
        },
      ],
    },
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
  dark: {
    name: "Tactical Dark",
    url: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
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
  chatOverlayFC?: GeoJSON.FeatureCollection | null;
  theme?: "light" | "dark";
}

export default function MapView({
  layers,
  onSelectDetection,
  onSelectAlert,
  visibleLayers,
  selectedDetectionId,
  centerCoordinates,
  chatOverlayFC,
  theme = "light",
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const deckOverlayRef = useRef<MapboxOverlay | null>(null);
  const loadedRef = useRef(false);
  const animFrameRef = useRef<number | null>(null);

  const isLight = theme === "light";
  const [currentStyle, setCurrentStyle] = useState<keyof typeof BASEMAP_STYLES>(
    theme === "light" ? "light" : "dark"
  );
  const [showDeckCurrents, setShowDeckCurrents] = useState(true);
  const [showDeck3DDriftArcs, setShowDeck3DDriftArcs] = useState(true);
  const [driftForecastTimeHour, setDriftForecastTimeHour] = useState<number>(72);
  const animTimeRef = useRef<number>(0);

  // Live CMEMS Currents state (initialized with STATIC_OCEAN_CURRENTS fallback for instant render)
  const [currentsData, setCurrentsData] = useState<{
    source: string;
    dataset_id?: string;
    isLive: boolean;
    vectors: Array<{ from: [number, number]; to: [number, number]; speed: number; region?: string; u?: number; v?: number }>;
  }>({
    source: "Synthetic Oceanic Model (Fallback)",
    isLive: false,
    vectors: STATIC_OCEAN_CURRENTS,
  });

  // Track latest props & state in ref for 60fps animation without triggering React re-renders
  const stateRef = useRef({
    layers,
    currentsData,
    showDeckCurrents,
    showDeck3DDriftArcs,
    driftForecastTimeHour,
    selectedDetectionId,
    chatOverlayFC,
    isLight,
    visibleLayers,
  });

  useEffect(() => {
    stateRef.current = {
      layers,
      currentsData,
      showDeckCurrents,
      showDeck3DDriftArcs,
      driftForecastTimeHour,
      selectedDetectionId,
      chatOverlayFC,
      isLight,
      visibleLayers,
    };
    updateDeckLayers(animTimeRef.current);
  }, [
    layers,
    currentsData,
    showDeckCurrents,
    showDeck3DDriftArcs,
    driftForecastTimeHour,
    selectedDetectionId,
    chatOverlayFC,
    isLight,
    visibleLayers,
  ]);

  // Fetch real-time Copernicus Marine (CMEMS) ocean currents from backend
  useEffect(() => {
    let isMounted = true;
    api
      .mapCurrents()
      .then((res) => {
        if (isMounted && res.vectors && res.vectors.length > 0) {
          setCurrentsData({
            source: res.source || "Copernicus Marine Service (CMEMS)",
            dataset_id: res.dataset_id,
            isLive: (res.source || "").toLowerCase().includes("copernicus"),
            vectors: res.vectors,
          });
        }
      })
      .catch((err) => {
        console.warn("[MapView] Could not fetch live CMEMS currents, using fallback field", err);
      });

    return () => {
      isMounted = false;
    };
  }, []);

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
      updateDeckLayers(0);
    });

    // Start continuous particle animation loop (direct to WebGL, no React re-render overhead)
    let lastT = performance.now();
    const animate = (now: number) => {
      const dt = Math.min((now - lastT) / 1000, 0.1);
      lastT = now;
      animTimeRef.current = (animTimeRef.current + dt * 0.45) % 1000.0;
      updateDeckLayers(animTimeRef.current);
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

  // Switch basemap when theme changes
  useEffect(() => {
    const targetStyle = theme === "light" ? "light" : "dark";
    if (mapRef.current && currentStyle !== targetStyle) {
      switchBasemap(targetStyle);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  // Dynamic speed-based color mapping for ocean currents
  function getVelocityColor(speed: number, lightTheme: boolean): [number, number, number, number] {
    if (speed < 0.22) {
      // Gentle calm drift: Deep ocean blue / Cyan
      return lightTheme ? [2, 132, 199, 210] : [56, 189, 248, 220];
    } else if (speed < 0.52) {
      // Moderate oceanic flow: Electric turquoise / Emerald
      return lightTheme ? [13, 148, 136, 235] : [45, 212, 191, 235];
    } else {
      // Swift jet / Somali current / Equatorial jet: Glowing Amber / Sea-coral
      return lightTheme ? [234, 88, 12, 245] : [251, 146, 60, 255];
    }
  }

  function updateDeckLayers(currentAnimTime: number = animTimeRef.current) {
    if (!deckOverlayRef.current) return;
    const {
      layers: curLayers,
      currentsData: curData,
      showDeckCurrents: curShowCurrents,
      showDeck3DDriftArcs: curShowArcs,
      driftForecastTimeHour: curDriftHour,
      selectedDetectionId: curSelId,
      chatOverlayFC: curChatFC,
      isLight: curIsLight,
      visibleLayers: curVisLayers,
    } = stateRef.current;

    const deckLayers: any[] = [];
    const isCurrentsActive = (curVisLayers.oceanCurrents !== undefined ? curVisLayers.oceanCurrents : curShowCurrents);

    // 1. Deck.gl Dynamic Fluid Ocean Current Streamlines & Particles (Live CMEMS)
    if (isCurrentsActive) {
      const streamLines: any[] = [];
      const flowingStreaks: any[] = [];
      const particleHeads: any[] = [];

      curData.vectors.forEach((c, i) => {
        const velColor = getVelocityColor(c.speed, curIsLight);
        const dx = c.to[0] - c.from[0];
        const dy = c.to[1] - c.from[1];

        // Background subtle streamline trace
        streamLines.push({
          from: c.from,
          to: c.to,
          color: curIsLight ? [186, 230, 253, 110] : [6, 182, 212, 40],
        });

        // 2 phase-staggered particles per vector for continuous fluid density
        const phases = [0.0, 0.5];
        phases.forEach((phase) => {
          const speedMultiplier = 0.7 + Math.min(1.8, c.speed * 2.2);
          const offset = ((currentAnimTime * speedMultiplier + i * 0.07 + phase) % 1.0);

          const headLon = c.from[0] + dx * offset;
          const headLat = c.from[1] + dy * offset;

          // Comet tail trailing behind the head in vector direction
          const tailFrac = 0.28;
          const tailLon = headLon - dx * tailFrac;
          const tailLat = headLat - dy * tailFrac;

          flowingStreaks.push({
            from: [tailLon, tailLat],
            to: [headLon, headLat],
            color: velColor,
          });

          particleHeads.push({
            position: [headLon, headLat],
            radius: 2.2 + Math.min(2.4, c.speed * 2.2),
            color: velColor,
          });
        });
      });

      // Ambient streamline trajectories
      deckLayers.push(
        new LineLayer({
          id: "deck-ocean-streamlines",
          data: streamLines,
          getSourcePosition: (d: any) => d.from,
          getTargetPosition: (d: any) => d.to,
          getColor: (d: any) => d.color,
          getWidth: 1.2,
          widthUnits: "pixels",
          pickable: false,
        })
      );

      // Dynamic animated comet streaks
      deckLayers.push(
        new LineLayer({
          id: "deck-ocean-flowing-streaks",
          data: flowingStreaks,
          getSourcePosition: (d: any) => d.from,
          getTargetPosition: (d: any) => d.to,
          getColor: (d: any) => d.color,
          getWidth: 1.8,
          widthUnits: "pixels",
          pickable: false,
        })
      );

      // Glowing flowing streamlet heads
      deckLayers.push(
        new ScatterplotLayer({
          id: "deck-ocean-current-heads",
          data: particleHeads,
          getPosition: (d: any) => d.position,
          radiusUnits: "pixels",
          getRadius: (d: any) => d.radius,
          radiusMinPixels: 1.8,
          radiusMaxPixels: 4.8,
          getFillColor: (d: any) => d.color,
          stroked: true,
          getLineColor: [255, 255, 255, 230],
          getLineWidth: 1,
          lineWidthUnits: "pixels",
          pickable: false,
        })
      );
    }

    // 2. Deck.gl 3D Elevated Parabolic Drift Arcs
    if (curShowArcs && curLayers.trajectories) {
      const arcData: any[] = [];

      // Extract trajectories grouped by detection
      const detCoordsMap = new Map<string, [number, number]>();
      curLayers.detections.features.forEach((f) => {
        detCoordsMap.set(f.properties.external_id, f.geometry.coordinates as [number, number]);
      });

      curLayers.trajectories.features.forEach((f) => {
        if (f.geometry.type === "LineString" && f.geometry.coordinates.length >= 2) {
          const detId = f.properties.detection_id;
          const forecastHour = f.properties.forecast_hour;

          // Only show up to current scrubber hour
          if (forecastHour <= curDriftHour) {
            const start = f.geometry.coordinates[0];
            const end = f.geometry.coordinates[1];
            const isSelected = detId === curSelId;

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
    const detectionPoints = curLayers.detections.features.map((f) => ({
      coordinates: f.geometry.coordinates,
      external_id: f.properties.external_id,
      confidence: f.properties.confidence,
      status: f.properties.incident_status || f.properties.status,
      isSelected: f.properties.external_id === curSelId,
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

    // 4. Chat overlay: route line, corridor polygon, hotspot markers
    if (curChatFC && curChatFC.features.length > 0) {
      const routeFeatures = curChatFC.features.filter(
        (f) => f.properties?.layer === "route"
      );
      const corridorFeatures = curChatFC.features.filter(
        (f) => f.properties?.layer === "corridor"
      );
      const hotspotFeatures = curChatFC.features.filter(
        (f) => f.properties?.layer === "hotspot"
      );

      // Route line
      if (routeFeatures.length > 0) {
        const routePaths = routeFeatures.map((f) => ({
          path: (f.geometry as GeoJSON.LineString).coordinates,
        }));
        deckLayers.push(
          new PathLayer({
            id: "chat-route-path",
            data: routePaths,
            getPath: (d: any) => d.path,
            getColor: [14, 165, 233, 230], // sky-500
            getWidth: 4,
            widthUnits: "pixels",
            widthMinPixels: 3,
            pickable: false,
          })
        );
      }

      // Corridor polygon
      if (corridorFeatures.length > 0) {
        const corridorPolygons = corridorFeatures.map((f) => ({
          contour: (f.geometry as GeoJSON.Polygon).coordinates[0],
        }));
        deckLayers.push(
          new PolygonLayer({
            id: "chat-corridor-fill",
            data: corridorPolygons,
            getPolygon: (d: any) => d.contour,
            getFillColor: [14, 165, 233, 28], // very translucent sky blue
            getLineColor: [14, 165, 233, 120],
            getLineWidth: 2,
            lineWidthUnits: "pixels",
            stroked: true,
            filled: true,
            pickable: false,
          })
        );
      }

      // Hotspot markers
      if (hotspotFeatures.length > 0) {
        const hotspotPoints = hotspotFeatures.map((f) => ({
          coords: (f.geometry as GeoJSON.Point).coordinates,
          count: f.properties?.count ?? 1,
          object_class: f.properties?.object_class ?? "unknown",
        }));
        deckLayers.push(
          new ScatterplotLayer({
            id: "chat-hotspot-markers",
            data: hotspotPoints,
            getPosition: (d: any) => d.coords,
            getRadius: (d: any) => 18000 + d.count * 4000,
            radiusMinPixels: 10,
            radiusMaxPixels: 40,
            getFillColor: (d: any) =>
              d.object_class.includes("ghost") ? [168, 85, 247, 220] : [251, 146, 60, 220],
            stroked: true,
            getLineColor: [255, 255, 255, 200],
            getLineWidth: 2,
            lineWidthUnits: "pixels",
            pickable: true,
          })
        );
      }
    }

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
    // Enrich basemap with vibrant, rich, aesthetic ocean & natural terrestrial colors
    if (currentStyle === "light") {
      // 1. Ocean & Sea Waters - rich, luminous, deep tropical marine azure
      if (map.getLayer("water")) {
        try {
          map.setPaintProperty("water", "fill-color", "#3d95df");
        } catch {}
      }

      // 2. Coastal Shelf / Water Shadow
      if (map.getLayer("water_shadow")) {
        try {
          map.setPaintProperty("water_shadow", "fill-color", "#2477c4");
          map.setPaintProperty("water_shadow", "fill-opacity", 0.7);
        } catch {}
      }

      // 3. Rivers & Waterways
      if (map.getLayer("waterway")) {
        try {
          map.setPaintProperty("waterway", "line-color", "#257cc7");
          map.setPaintProperty("waterway", "line-width", 1.8);
        } catch {}
      }

      // 4. Land base - natural warm lush sage/earth terrain
      if (map.getLayer("background")) {
        try {
          map.setPaintProperty("background", "background-color", "#e8f2df");
        } catch {}
      }

      // 5. Landcover (Forests, vegetation) - rich emerald green
      if (map.getLayer("landcover")) {
        try {
          map.setPaintProperty("landcover", "fill-color", "#bde4ad");
          map.setPaintProperty("landcover", "fill-opacity", 0.85);
        } catch {}
      }

      // 6. National parks & sanctuaries - vivid vibrant green
      if (map.getLayer("park_national_park")) {
        try {
          map.setPaintProperty("park_national_park", "fill-color", "#93d47d");
        } catch {}
      }
      if (map.getLayer("park_nature_reserve")) {
        try {
          map.setPaintProperty("park_nature_reserve", "fill-color", "#a5dc93");
        } catch {}
      }

      // 7. General landuse - warm sandy coastal landuse
      if (map.getLayer("landuse")) {
        try {
          map.setPaintProperty("landuse", "fill-color", "#f2edd9");
        } catch {}
      }

      // 8. Administrative boundaries
      if (map.getLayer("boundary_state")) {
        try {
          map.setPaintProperty("boundary_state", "line-color", "#6c936c");
          map.setPaintProperty("boundary_state", "line-width", 1.2);
        } catch {}
      }
    }

    // 1. Protected Areas (WDPA) - Lush Emerald
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
          "fill-opacity": 0.32,
        },
      });
      map.addLayer({
        id: "protected-areas-line",
        type: "line",
        source: "protected-areas",
        paint: {
          "line-color": "#047857",
          "line-width": 2.2,
          "line-dasharray": [3, 2],
        },
      });
    }

    // 2. Coral Reefs (GCRMN / UNEP-WCMC) - Electric Turquoise
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
          "fill-color": "#00f0ff",
          "fill-opacity": 0.42,
        },
      });
      map.addLayer({
        id: "coral-reefs-line",
        type: "line",
        source: "coral-reefs",
        paint: {
          "line-color": "#0284c7",
          "line-width": 2.4,
        },
      });
    }

    // 3. Species & Habitats (SWOT / OBIS-SEAMAP) - Royal Violet/Magenta
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
          "fill-opacity": 0.32,
        },
      });
      map.addLayer({
        id: "species-habitats-line",
        type: "line",
        source: "species-habitats",
        paint: {
          "line-color": "#7c3aed",
          "line-width": 2.0,
          "line-dasharray": [2, 2],
        },
      });
    }

    // 4. Drift Trajectory Uncertainty Cones - Luminous Amber
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
          "fill-color": "#f59e0b",
          "fill-opacity": 0.26,
        },
      });
      map.addLayer({
        id: "uncertainty-stroke",
        type: "line",
        source: "trajectories",
        filter: ["==", ["get", "layer"], "uncertainty_polygon"],
        paint: {
          "line-color": "#d97706",
          "line-width": 1.8,
          "line-dasharray": [4, 3],
        },
      });
    }

    // 5. High-Risk Zones - Vibrant Coral Rose / Crimson
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
            "CRITICAL", "#f43f5e",
            "HIGH", "#fb923c",
            "#facc15",
          ],
          "fill-opacity": 0.35,
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
            "CRITICAL", "#e11d48",
            "HIGH", "#ea580c",
            "#ca8a04",
          ],
          "line-width": 2.0,
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
          "circle-stroke-color": isLight ? "#ffffff" : "#091224",
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
      <div 
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        className={`pointer-events-auto absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 rounded-2xl border px-4 py-2.5 shadow-2xl backdrop-blur-md transition-colors ${
        isLight
          ? "border-slate-200/90 bg-white/95 text-slate-800 shadow-slate-900/10"
          : "border-sky-500/25 bg-slate-950/90 text-slate-300 shadow-2xl"
      }`}>
        {/* Ocean Current Flow Toggle with Live CMEMS Badge */}
        <button
          onClick={() => setShowDeckCurrents((prev) => !prev)}
          className={`flex items-center gap-2 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
            showDeckCurrents
              ? isLight
                ? "bg-sky-50 text-sky-700 border border-sky-300 shadow-sm"
                : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/20"
              : isLight
                ? "text-slate-500 hover:text-slate-800 border border-slate-200"
                : "text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
          title={
            currentsData.isLive
              ? `Live Copernicus Marine Service (${currentsData.vectors.length} hydrodynamic vectors active)`
              : "Toggle Animated Ocean Current Particle Streamlines"
          }
        >
          <span className={showDeckCurrents ? "animate-pulse" : ""}>🌊</span>
          <span>{currentsData.isLive ? "CMEMS Ocean Flow" : "Ocean Current Flow"}</span>
          {currentsData.isLive && (
            <span className={`flex items-center gap-1 rounded border px-1 py-0.2 text-[9px] font-bold tracking-wider ${
              isLight ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "bg-emerald-950/80 border-emerald-500/40 text-emerald-400"
            }`}>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping" />
              LIVE
            </span>
          )}
        </button>

        {/* 3D Drift Arcs Toggle */}
        <button
          onClick={() => setShowDeck3DDriftArcs((prev) => !prev)}
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
            showDeck3DDriftArcs
              ? isLight
                ? "bg-amber-50 text-amber-700 border border-amber-300 shadow-sm"
                : "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/20"
              : isLight
                ? "text-slate-500 hover:text-slate-800 border border-slate-200"
                : "text-slate-400 hover:text-slate-200 border border-slate-800"
          }`}
          title="Toggle 3D Elevated Parabolic Drift Arcs"
        >
          <span>⚡</span>
          <span>3D Drift Arcs</span>
        </button>

        <div className={`h-5 w-px ${isLight ? "bg-slate-200" : "bg-slate-800"}`} />

        {/* 72-Hour Forecast Time Scrubber Slider */}
        <div className={`flex items-center gap-2.5 text-xs ${isLight ? "text-slate-700" : "text-slate-300"}`}>
          <span className={`font-semibold text-[11px] whitespace-nowrap ${isLight ? "text-slate-600" : "text-slate-400"}`}>
            Drift Forecast: <strong className={isLight ? "text-sky-600" : "text-sky-400"}>+{driftForecastTimeHour}h</strong>
          </span>
          <input
            type="range"
            min="0"
            max="72"
            step="24"
            value={driftForecastTimeHour}
            onChange={(e) => setDriftForecastTimeHour(Number(e.target.value))}
            className={`w-24 accent-sky-500 cursor-pointer h-1.5 rounded-lg ${isLight ? "bg-slate-200" : "bg-slate-800"}`}
          />
          <div className={`flex gap-1 text-[9px] font-bold ${isLight ? "text-slate-600" : "text-slate-400"}`}>
            {[0, 24, 48, 72].map((h) => (
              <button
                key={h}
                onClick={() => setDriftForecastTimeHour(h)}
                className={`rounded px-1.5 py-0.5 ${
                  driftForecastTimeHour === h ? "bg-sky-500 text-white" : isLight ? "hover:text-slate-900" : "hover:text-slate-200"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Basemap Switcher Control in bottom-right */}
      <div 
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        className={`absolute bottom-6 right-4 z-10 flex items-center rounded-xl border p-1 shadow-xl backdrop-blur transition-colors ${
        isLight
          ? "border-slate-200/90 bg-white/95 text-slate-800 shadow-slate-900/10"
          : "border-sky-950 bg-slate-900/90 text-slate-400 shadow-xl"
      }`}>
        {(["light", "ocean", "satellite", "dark"] as const).map((key) => (
          <button
            key={key}
            onClick={() => switchBasemap(key)}
            className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
              currentStyle === key
                ? "bg-sky-500 text-white shadow-sm font-semibold"
                : isLight
                  ? "text-slate-600 hover:text-slate-900"
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
