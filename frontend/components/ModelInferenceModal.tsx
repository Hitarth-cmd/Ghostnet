"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  MarineModelInfo,
  MarinePredictionResult,
} from "@/types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onDetectionPlotted?: () => void;
}

const GEE_REGIONS = [
  {
    id: "goa_offshore",
    name: "Goa Offshore Waters",
    description: "Arabian Sea coastal waters & Mandovi plume",
    lat: 15.20,
    lon: 72.85,
  },
  {
    id: "mumbai_offshore",
    name: "Mumbai Offshore",
    description: "High vessel traffic & macro-plastic corridor",
    lat: 18.80,
    lon: 72.15,
  },
  {
    id: "gulf_of_mannar",
    name: "Gulf of Mannar",
    description: "Sensitive coral barrier & turtle habitats",
    lat: 8.85,
    lon: 79.45,
  },
  {
    id: "lakshadweep_atoll",
    name: "Lakshadweep Waters",
    description: "Coral lagoons & pelagic fish corridors",
    lat: 10.55,
    lon: 72.45,
  },
  {
    id: "andaman_waters",
    name: "Andaman Pelagic Zone",
    description: "Deep sea ghost-gear drift corridor",
    lat: 11.60,
    lon: 93.15,
  },
  {
    id: "kochi_offshore",
    name: "Kochi Offshore",
    description: "Southwest coastal upwelling & fishery zone",
    lat: 9.80,
    lon: 75.60,
  },
];

export default function ModelInferenceModal({
  isOpen,
  onClose,
  onDetectionPlotted,
}: Props) {
  const [sourceMode, setSourceMode] = useState<"earthengine" | "upload">("earthengine");
  const [modelInfo, setModelInfo] = useState<MarineModelInfo | null>(null);
  const [geeStatus, setGeeStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overlay" | "mask" | "rgb">("overlay");
  const [result, setResult] = useState<any>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [plotToMap, setPlotToMap] = useState(true);

  // Earth Engine parameters
  const [selectedRegionId, setSelectedRegionId] = useState("goa_offshore");
  const [customLat, setCustomLat] = useState("15.20");
  const [customLon, setCustomLon] = useState("72.85");

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      if (!modelInfo) {
        api.getModelInfo()
          .then(setModelInfo)
          .catch((err) => console.warn("Failed to load model info:", err));
      }
      if (!geeStatus) {
        api.getEarthEngineStatus()
          .then(setGeeStatus)
          .catch((err) => console.warn("Failed to load GEE status:", err));
      }
    }
  }, [isOpen, modelInfo, geeStatus]);

  if (!isOpen) return null;

  function handleSelectRegion(region: typeof GEE_REGIONS[0]) {
    setSelectedRegionId(region.id);
    setCustomLat(region.lat.toString());
    setCustomLon(region.lon.toString());
  }

  async function handleEarthEngineScan() {
    setError(null);
    setLoading(true);
    try {
      const lat = parseFloat(customLat);
      const lon = parseFloat(customLon);
      if (isNaN(lat) || isNaN(lon)) {
        throw new Error("Please enter valid decimal coordinates (e.g. 15.20, 72.85)");
      }

      const data = await api.scanEarthEngine({
        latitude: lat,
        longitude: lon,
        pixel_size_meters: 10.0,
        plot_to_map: plotToMap,
      });

      setResult(data);
      if (plotToMap && data.created_detections && data.created_detections.length > 0) {
        onDetectionPlotted?.();
      }
    } catch (err: any) {
      setError(err.message || "Earth Engine satellite ingestion failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUploadAndPredict(file: File) {
    setError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("pixel_size_meters", "10.0");
      formData.append("plot_to_map", plotToMap ? "true" : "false");

      const data = await api.predictMarineDebris(formData);
      setResult(data);
      if (plotToMap && data.created_detections && data.created_detections.length > 0) {
        onDetectionPlotted?.();
      }
    } catch (err: any) {
      setError(err.message || "Prediction failed. Ensure image format is supported.");
    } finally {
      setLoading(false);
    }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleUploadAndPredict(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUploadAndPredict(file);
  }

  const severityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "border-red-500/50 bg-red-950/80 text-red-300";
      case "HIGH":
        return "border-orange-500/50 bg-orange-950/80 text-orange-300";
      case "MODERATE":
        return "border-yellow-500/50 bg-yellow-950/80 text-yellow-300";
      default:
        return "border-emerald-500/50 bg-emerald-950/80 text-emerald-300";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
      <div className="relative flex max-h-[92vh] w-full max-w-5xl flex-col rounded-2xl border border-sky-500/30 bg-slate-950 text-slate-100 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 text-sky-400">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">
                  Sentinel-2 Live Earth Engine &amp; Marine Debris AI
                </h2>
                <span className="rounded bg-sky-500/20 px-2 py-0.5 text-[10px] font-bold text-sky-300">
                  balmy-ocean-509105-v8
                </span>
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                  val mIoU: 71.96%
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Automated Sentinel-2 L2A ingestion via Google Earth Engine API paired with domain-adapted ViT-UNet++
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Source Mode Switcher */}
        <div className="flex border-b border-slate-800 bg-slate-900/60 px-6 py-2.5">
          <div className="flex gap-2">
            <button
              onClick={() => setSourceMode("earthengine")}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                sourceMode === "earthengine"
                  ? "bg-sky-600 text-white shadow-md"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <span>🛰️</span>
              <span>Google Earth Engine API (No File Needed)</span>
            </button>
            <button
              onClick={() => setSourceMode("upload")}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                sourceMode === "upload"
                  ? "bg-sky-600 text-white shadow-md"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <span>📁</span>
              <span>Upload Local GeoTIFF / Image</span>
            </button>
          </div>
        </div>

        {/* Content body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Earth Engine Mode View */}
          {sourceMode === "earthengine" && (
            <div className="space-y-4">
              {/* Hotspot Presets */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Select Indian Marine Observation Target (Sentinel-2 L2A)
                </label>
                <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2.5">
                  {GEE_REGIONS.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => handleSelectRegion(r)}
                      className={`flex flex-col text-left rounded-xl p-3 border transition ${
                        selectedRegionId === r.id
                          ? "border-sky-500 bg-sky-950/40 shadow-sm"
                          : "border-slate-800 bg-slate-900/50 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-200">{r.name}</span>
                        {selectedRegionId === r.id && (
                          <span className="text-[10px] text-sky-400">● Selected</span>
                        )}
                      </div>
                      <span className="mt-1 text-[10px] text-slate-400 leading-tight">
                        {r.description}
                      </span>
                      <span className="mt-1 font-mono text-[9px] text-slate-500">
                        {r.lat.toFixed(2)}°N, {r.lon.toFixed(2)}°E
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Coordinates and Trigger Card */}
              <div className="flex flex-col md:flex-row items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex items-center gap-3 w-full md:w-auto">
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase">Latitude (°N)</label>
                    <input
                      type="text"
                      value={customLat}
                      onChange={(e) => {
                        setCustomLat(e.target.value);
                        setSelectedRegionId("");
                      }}
                      className="mt-1 w-28 rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase">Longitude (°E)</label>
                    <input
                      type="text"
                      value={customLon}
                      onChange={(e) => {
                        setCustomLon(e.target.value);
                        setSelectedRegionId("");
                      }}
                      className="mt-1 w-28 rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                    />
                  </div>
                  <div className="pt-4">
                    <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={plotToMap}
                        onChange={(e) => setPlotToMap(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-800 text-sky-500"
                      />
                      <span>Plot to live GIS map</span>
                    </label>
                  </div>
                </div>

                <button
                  disabled={loading}
                  onClick={handleEarthEngineScan}
                  className="w-full md:w-auto flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg transition hover:bg-sky-500 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      <span>Ingesting GEE Sentinel-2 &amp; Running Model...</span>
                    </>
                  ) : (
                    <>
                      <span>🛰️ Fetch from GEE &amp; Scan Debris</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* File Upload Mode View */}
          {sourceMode === "upload" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
                isDragging
                  ? "border-sky-400 bg-sky-950/30"
                  : "border-slate-700 bg-slate-900/60 hover:border-sky-500/60 hover:bg-slate-900"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".tif,.tiff,.png,.jpg,.jpeg"
                onChange={onFileChange}
                className="hidden"
              />
              <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-sky-500/10 text-sky-400">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <p className="text-sm font-semibold text-slate-200">
                Drop Sentinel-2 GeoTIFF (.tif) or satellite crop here
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Supports 11-channel Sentinel-2 L2A tiles or standard RGB satellite imagery
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-500/50 bg-red-950/70 p-4 text-xs text-red-200">
              ⚠️ {error}
            </div>
          )}

          {/* Results section */}
          {result && (
            <div className="space-y-6 pt-2">
              {/* Ingestion Metadata Bar */}
              {result.gee_metadata && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-500/30 bg-sky-950/30 px-4 py-2.5 text-xs text-sky-200">
                  <div className="flex items-center gap-2">
                    <span className="font-bold">🛰️ Data Source:</span>
                    <span>{result.gee_metadata.source}</span>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] text-slate-300">
                    <span>Scene: <code className="font-mono text-sky-300">{result.gee_metadata.scene_id}</code></span>
                    <span>Acquisition: <strong className="text-slate-100">{result.gee_metadata.acquisition_date}</strong></span>
                    <span>Cloud: <strong className="text-slate-100">{result.gee_metadata.cloud_coverage_pct}%</strong></span>
                  </div>
                </div>
              )}

              {/* Analytics Header Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Marine Debris Area</div>
                  <div className="mt-1 text-lg font-extrabold text-red-400">
                    {result.summary.debris_area_m2.toLocaleString()} m²
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {result.summary.debris_area_km2} km² ({result.summary.debris_pixel_count} px)
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Debris Coverage</div>
                  <div className="mt-1 text-lg font-extrabold text-sky-400">
                    {result.summary.debris_percentage}%
                  </div>
                  <div className="text-[10px] text-slate-400">
                    of ocean surface scanned
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Model Confidence</div>
                  <div className="mt-1 text-lg font-extrabold text-emerald-400">
                    {result.summary.debris_mean_confidence > 0
                      ? `${(result.summary.debris_mean_confidence * 100).toFixed(1)}%`
                      : "Clear Waters"}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    ViT-UNet++ class probability
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Threat Severity</div>
                  <div className="mt-1">
                    <span className={`inline-block rounded-md border px-2 py-0.5 text-xs font-black ${severityBadge(result.summary.severity_level)}`}>
                      {result.summary.severity_level}
                    </span>
                  </div>
                  <div className="mt-1 text-[10px] text-slate-400 truncate" title={result.summary.recommended_action}>
                    {result.summary.recommended_action}
                  </div>
                </div>
              </div>

              {/* Visualizations and Class breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Visualizer Frame (7 cols) */}
                <div className="lg:col-span-7 flex flex-col rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  {/* View mode toggle tabs */}
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
                    <div className="text-xs font-bold text-slate-300">
                      Satellite Visualizer ({result.summary.image_dimensions.width}×{result.summary.image_dimensions.height})
                    </div>
                    <div className="flex gap-1 rounded-lg bg-slate-950 p-1 border border-slate-800">
                      <button
                        onClick={() => setActiveTab("overlay")}
                        className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                          activeTab === "overlay"
                            ? "bg-sky-600 text-white"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Debris Overlay
                      </button>
                      <button
                        onClick={() => setActiveTab("mask")}
                        className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                          activeTab === "mask"
                            ? "bg-sky-600 text-white"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        11-Class Mask
                      </button>
                      <button
                        onClick={() => setActiveTab("rgb")}
                        className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                          activeTab === "rgb"
                            ? "bg-sky-600 text-white"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        RGB Quicklook
                      </button>
                    </div>
                  </div>

                  {/* Image container */}
                  <div className="relative aspect-square w-full overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center border border-slate-800">
                    {activeTab === "overlay" && (
                      <img
                        src={result.visualizations.debris_overlay}
                        alt="Debris Overlay"
                        className="h-full w-full object-contain"
                      />
                    )}
                    {activeTab === "mask" && (
                      <img
                        src={result.visualizations.segmentation_mask}
                        alt="11-Class Segmentation Mask"
                        className="h-full w-full object-contain"
                      />
                    )}
                    {activeTab === "rgb" && (
                      <img
                        src={result.visualizations.rgb_quicklook}
                        alt="Sentinel-2 RGB Quicklook"
                        className="h-full w-full object-contain"
                      />
                    )}
                  </div>
                </div>

                {/* Class Breakdown List (5 cols) */}
                <div className="lg:col-span-5 flex flex-col rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="border-b border-slate-800 pb-2 mb-3">
                    <div className="text-xs font-bold text-slate-300">
                      MARIDA / MADOS Semantic Spectrum
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Multi-spectral optical pixel classification
                    </div>
                  </div>

                  <div className="flex-1 space-y-2 overflow-y-auto max-h-[360px] pr-1">
                    {result.class_breakdown
                      .filter((c: any) => c.pixel_count > 0 || c.class_id === 0)
                      .map((c: any) => (
                        <div
                          key={c.class_id}
                          className="rounded-lg border border-slate-800/80 bg-slate-950/70 p-2.5 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span
                                className="h-3 w-3 rounded-sm inline-block shadow"
                                style={{ backgroundColor: c.color }}
                              />
                              <span className="font-semibold text-slate-200">{c.name}</span>
                            </div>
                            <span className="font-mono font-bold text-slate-300">
                              {c.percentage}%
                            </span>
                          </div>
                          <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${Math.min(100, Math.max(1, c.percentage))}%`,
                                backgroundColor: c.color,
                              }}
                            />
                          </div>
                          <div className="mt-1 flex justify-between text-[10px] text-slate-400">
                            <span>{c.pixel_count.toLocaleString()} px</span>
                            <span>{c.area_m2.toLocaleString()} m²</span>
                          </div>
                        </div>
                      ))}
                  </div>

                  {result.created_detections && result.created_detections.length > 0 && (
                    <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-950/40 p-2.5 text-xs text-emerald-200 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span>✓</span>
                        <span>{result.created_detections.length} Marine debris targets plotted to live map!</span>
                      </div>
                      <button
                        onClick={onClose}
                        className="rounded bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white hover:bg-emerald-500"
                      >
                        View on Map
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
