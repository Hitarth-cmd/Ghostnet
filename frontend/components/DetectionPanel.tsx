"use client";

import { useEffect, useState } from "react";
import type { AnalysisResult, Detection, SatellitePreviewResponse } from "@/types";
import { api } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  LOW: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  MEDIUM: "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  HIGH: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  CRITICAL: "text-rose-400 bg-rose-500/10 border-rose-500/30",
};

const STATUS_BADGE: Record<string, string> = {
  unverified: "bg-red-500/20 text-red-300 border-red-500/40",
  verified: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
  assigned: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  being_handled: "bg-purple-500/20 text-purple-300 border-purple-500/40",
  resolved: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  recovered: "bg-sky-500/20 text-sky-300 border-sky-500/40",
  rejected: "bg-slate-500/20 text-slate-400 border-slate-500/40",
};

interface DetectionPanelProps {
  detection: Detection | null;
  onAnalyzed: () => void;
  onOpenResponderWithDetection?: (externalId: string) => void;
  onClose?: () => void;
}

export default function DetectionPanel({
  detection,
  onAnalyzed,
  onOpenResponderWithDetection,
  onClose,
}: DetectionPanelProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SatellitePreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTab, setPreviewTab] = useState<"overlay" | "mask" | "rgb">("overlay");

  // When detection changes, reset or load initial report and satellite preview
  useEffect(() => {
    setAnalysis(null);
    setError(null);
    if (!detection?.external_id) {
      setPreview(null);
      return;
    }
    setPreviewLoading(true);
    api.getSatellitePreview(detection.external_id)
      .then((data) => setPreview(data))
      .catch((err) => {
        console.warn("Satellite preview fetch error:", err);
        setPreview(null);
      })
      .finally(() => setPreviewLoading(false));
  }, [detection?.external_id]);

  if (!detection) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center text-sm text-slate-400">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-sky-500/20 bg-sky-500/10 text-sky-400">
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div className="text-base font-bold text-slate-200">Interactive Marine Target Inspector</div>
        <p className="mt-1 text-xs text-slate-400 max-w-xs">
          Select any detection marker, drift cone, or threatened habitat on the map to review telemetry, risk metrics, and trigger multi-agent analysis.
        </p>
      </div>
    );
  }

  async function handleRunPipeline() {
    if (!detection) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.analyzeSync(detection.external_id);
      setAnalysis(result);
      onAnalyzed();
    } catch (e: any) {
      setError(e.message || "Multi-agent pipeline failed");
    } finally {
      setLoading(false);
    }
  }

  const isActionable = detection.confidence >= 0.70;
  const currentStatus = detection.incident_status || detection.status;

  return (
    <div className="flex h-full flex-col overflow-hidden text-sm">
      {/* Top Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold uppercase tracking-wider text-sky-400">
            Satellite Observation
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          )}
        </div>

        <div className="mt-1 flex items-center justify-between">
          <h2 className="text-xl font-extrabold text-slate-100">{detection.external_id}</h2>
          <span
            className={`rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase ${
              STATUS_BADGE[currentStatus] || STATUS_BADGE.unverified
            }`}
          >
            {currentStatus.replaceAll("_", " ")}
          </span>
        </div>

        <div className="mt-1 text-xs text-slate-300 capitalize">
          {detection.object_class.replaceAll("_", " ")}
        </div>

        {/* Confidence Progress Meter */}
        <div className="mt-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-slate-400">AI Confidence:</span>
            <span className={`font-bold ${isActionable ? "text-emerald-400" : "text-amber-400"}`}>
              {(detection.confidence * 100).toFixed(1)}%
              {isActionable ? " (Actionable Alert)" : " (Requires Human Review)"}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isActionable ? "bg-emerald-500" : "bg-amber-500"
              }`}
              style={{ width: `${Math.min(100, detection.confidence * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Scrollable details */}
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {/* Core telemetry */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-2.5">
            <div className="text-[10px] text-slate-500 uppercase">Latitude / Longitude</div>
            <div className="mt-0.5 font-semibold text-slate-200">
              {detection.latitude.toFixed(4)}°N, {detection.longitude.toFixed(4)}°E
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-2.5">
            <div className="text-[10px] text-slate-500 uppercase">Estimated Area</div>
            <div className="mt-0.5 font-semibold text-slate-200">
              {detection.area_m2 ? `${detection.area_m2.toFixed(1)} m²` : "Point Target"}
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-2.5">
            <div className="text-[10px] text-slate-500 uppercase">Detection Sensor</div>
            <div className="mt-0.5 font-semibold text-slate-200 capitalize">{detection.source}</div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-800/40 p-2.5">
            <div className="text-[10px] text-slate-500 uppercase">Observation Time</div>
            <div className="mt-0.5 font-semibold text-slate-200">
              {new Date(detection.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC
            </div>
          </div>
        </div>

        {/* Earth Engine Satellite Imagery & AI Segmentation Visualizer */}
        <div className="rounded-xl border border-sky-500/30 bg-slate-900/80 p-3.5 shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="text-base">🛰️</span>
              <div>
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-100">
                  <span>Sentinel-2 Satellite Image</span>
                  <span className="rounded bg-sky-500/20 px-1.5 py-0.2 text-[9px] font-bold text-sky-300">
                    GEE LIVE
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono truncate max-w-[170px]" title={detection.scene_id}>
                  {detection.scene_id || "Sentinel-2 L2A"}
                </div>
              </div>
            </div>

            {/* View Tab Selector */}
            <div className="flex rounded-lg border border-slate-700 bg-slate-950 p-0.5 text-[10px]">
              <button
                onClick={() => setPreviewTab("overlay")}
                className={`rounded px-2 py-0.5 font-bold transition ${
                  previewTab === "overlay" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                title="AI Debris Boundary Overlay"
              >
                Overlay
              </button>
              <button
                onClick={() => setPreviewTab("mask")}
                className={`rounded px-2 py-0.5 font-bold transition ${
                  previewTab === "mask" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                title="11-Class Semantic Segmentation Mask"
              >
                11-Mask
              </button>
              <button
                onClick={() => setPreviewTab("rgb")}
                className={`rounded px-2 py-0.5 font-bold transition ${
                  previewTab === "rgb" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
                title="Sentinel-2 Optical RGB Surface Reflectance"
              >
                RGB
              </button>
            </div>
          </div>

          {/* Image Display */}
          <div className="relative mt-3 aspect-video w-full overflow-hidden rounded-lg border border-slate-800 bg-slate-950 flex items-center justify-center">
            {previewLoading ? (
              <div className="flex flex-col items-center gap-2 text-xs text-slate-400">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                <span>Ingesting Sentinel-2 bands from Earth Engine...</span>
              </div>
            ) : preview?.visualizations ? (
              <>
                <img
                  src={
                    previewTab === "overlay"
                      ? preview.visualizations.debris_overlay
                      : previewTab === "mask"
                      ? preview.visualizations.segmentation_mask
                      : preview.visualizations.rgb_quicklook
                  }
                  alt={`Sentinel-2 ${previewTab}`}
                  className="h-full w-full object-cover"
                />
                <div className="absolute bottom-1.5 left-1.5 rounded bg-slate-950/85 px-2 py-0.5 text-[9px] font-mono text-sky-300 backdrop-blur border border-slate-800">
                  {previewTab === "overlay" && "🎯 AI Marine Debris (Red Cluster)"}
                  {previewTab === "mask" && "🔬 ViT-UNet++ 11-Class Semantic Mask"}
                  {previewTab === "rgb" && "🌍 Sentinel-2 L2A RGB Surface Reflectance"}
                </div>
              </>
            ) : (
              <div className="p-4 text-center text-xs text-slate-500">
                Satellite preview currently unavailable
              </div>
            )}
          </div>

          {/* Earth Engine Project & Model Provenance */}
          <div className="mt-2.5 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/80 pt-2">
            <span className="font-mono text-sky-400 font-semibold">
              EE: balmy-ocean-509105-v8
            </span>
            <span className="text-emerald-400 font-semibold">
              ViT-UNet++ (val mIoU 71.96%)
            </span>
          </div>

          {/* Top Detected Classes Breakdown */}
          {preview?.class_breakdown && (
            <div className="mt-2.5 space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Semantic Spectrum Distribution
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {preview.class_breakdown
                  .filter((c) => c.percentage > 0.05 || c.class_id === 0)
                  .slice(0, 4)
                  .map((c) => (
                    <div
                      key={c.class_id}
                      className="flex items-center justify-between rounded bg-slate-950/80 px-2 py-1 text-[10px] border border-slate-800"
                    >
                      <div className="flex items-center gap-1.5">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: c.color }}
                        />
                        <span className="text-slate-300 truncate max-w-[85px]">{c.name}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-200">
                        {c.percentage.toFixed(1)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Incident Assignment Banner */}
        {detection.assigned_team && (
          <div className="rounded-xl border border-sky-500/30 bg-sky-950/30 p-3 text-xs">
            <div className="font-semibold text-sky-300">Assigned Response Team:</div>
            <div className="text-slate-100 font-bold">{detection.assigned_team}</div>
            {detection.assigned_to && (
              <div className="text-slate-400 text-[11px]">Lead: {detection.assigned_to}</div>
            )}
            {detection.verification_notes && (
              <div className="mt-1.5 text-slate-300 italic text-[11px] border-t border-sky-900/50 pt-1">
                &ldquo;{detection.verification_notes}&rdquo;
              </div>
            )}
          </div>
        )}

        {/* Multi-Agent Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleRunPipeline}
            disabled={loading}
            className="flex-1 rounded-xl bg-sky-600 py-2.5 text-xs font-bold text-white shadow-lg transition hover:bg-sky-500 disabled:opacity-50"
          >
            {loading ? "Multi-Agent Pipeline Executing…" : "⚡ Run Multi-Agent Analysis"}
          </button>

          {onOpenResponderWithDetection && (
            <button
              onClick={() => onOpenResponderWithDetection(detection.external_id)}
              className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-bold text-amber-300 hover:bg-amber-500/20"
              title="Open Incident Operations"
            >
              Intervene
            </button>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-950/60 p-3 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Multi-Agent Results */}
        {analysis && (
          <div className="space-y-4 pt-2">
            {/* Drift Forecast */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-yellow-400">
                  Drift Agent Ensemble (OpenDrift)
                </span>
                <span className="rounded bg-yellow-400/10 px-1.5 py-0.5 text-[10px] text-yellow-300">
                  {analysis.drift.mode.toUpperCase()}
                </span>
              </div>
              <div className="mt-2.5 space-y-1.5">
                {analysis.drift.horizons.map((h) => (
                  <div key={h.forecast_hour} className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-300">+{h.forecast_hour}h Horizon:</span>
                    <span className="text-slate-400">
                      {h.mean_latitude.toFixed(3)}°N, {h.mean_longitude.toFixed(3)}°E
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Ecological Risk & Priority */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
                  Ecological Risk Agent
                </span>
                <span
                  className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase ${
                    RISK_COLORS[analysis.risk.risk_level]
                  }`}
                >
                  {analysis.risk.risk_level} (Score {analysis.risk.risk_score.toFixed(3)})
                </span>
              </div>

              <div className="mt-2.5 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Protected Area Overlap:</span>
                  <span className={analysis.geospatial.protected_area_overlap ? "text-rose-400 font-bold" : "text-slate-300"}>
                    {analysis.geospatial.protected_area_overlap ? "YES (Threat Confirmed)" : "None"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Coral Reef / Habitat Proximity:</span>
                  <span className={analysis.geospatial.habitat_overlap ? "text-rose-400 font-bold" : "text-slate-300"}>
                    {analysis.geospatial.habitat_overlap ? "YES" : `${analysis.geospatial.distance_to_nearest_protected_area_km.toFixed(1)} km`}
                  </span>
                </div>
                {analysis.geospatial.nearest_protected_area && (
                  <div className="text-[11px] text-slate-300 pt-1">
                    Nearest Ecological Zone: <strong>{analysis.geospatial.nearest_protected_area}</strong>
                  </div>
                )}
              </div>
            </div>

            {/* AI Synthesized Intelligence Report */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5">
              <div className="text-xs font-bold uppercase tracking-wider text-sky-400 mb-1.5">
                RAG & Evidence Agent Synthesis
              </div>
              <p className="text-xs leading-relaxed text-slate-200">{analysis.report.summary}</p>

              {analysis.report.evidence.length > 0 && (
                <div className="mt-3 space-y-2 border-t border-slate-800 pt-2">
                  <div className="text-[10px] uppercase font-bold text-slate-500">Cited Literature & Data Provenance</div>
                  {analysis.report.evidence.map((e, idx) => (
                    <div key={idx} className="rounded bg-slate-950/70 p-2 text-[11px] text-slate-300">
                      <div className="text-[9px] uppercase font-bold text-sky-400">{e.source}</div>
                      <div className="mt-0.5">{e.text}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
