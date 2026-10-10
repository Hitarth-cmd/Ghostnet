"use client";

import { useEffect, useState } from "react";
import type { AnalysisResult, Detection } from "@/types";
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
  theme?: "light" | "dark";
}

export default function DetectionPanel({
  detection,
  onAnalyzed,
  onOpenResponderWithDetection,
  onClose,
  theme = "light",
}: DetectionPanelProps) {
  const isLight = theme === "light";
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When detection changes, reset or load initial report
  useEffect(() => {
    setAnalysis(null);
    setError(null);
  }, [detection?.external_id]);

  if (!detection) {
    return (
      <div className={`flex h-full flex-col items-center justify-center p-8 text-center text-sm ${isLight ? "text-slate-500" : "text-slate-400"}`}>
        <div className={`mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border ${
          isLight ? "border-sky-300 bg-sky-50 text-sky-600" : "border-sky-500/20 bg-sky-500/10 text-sky-400"
        }`}>
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div className={`text-base font-bold ${isLight ? "text-slate-900" : "text-slate-200"}`}>Interactive Marine Target Inspector</div>
        <p className={`mt-1 text-xs max-w-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
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
      <div className={`border-b p-5 transition-colors ${
        isLight ? "border-slate-200 bg-slate-50/90 text-slate-900" : "border-slate-800 bg-slate-900/60 text-slate-100"
      }`}>
        <div className="flex items-center justify-between">
          <span className={`text-[10px] font-bold uppercase tracking-wider ${isLight ? "text-sky-600" : "text-sky-400"}`}>
            Satellite Observation
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className={`${isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-400 hover:text-white"}`}
            >
              ✕
            </button>
          )}
        </div>

        <div className="mt-1 flex items-center justify-between">
          <h2 className={`text-xl font-extrabold ${isLight ? "text-slate-900" : "text-slate-100"}`}>{detection.external_id}</h2>
          <span
            className={`rounded-md border px-2 py-0.5 text-[11px] font-bold uppercase ${
              STATUS_BADGE[currentStatus] || STATUS_BADGE.unverified
            }`}
          >
            {currentStatus.replaceAll("_", " ")}
          </span>
        </div>

        <div className={`mt-1 text-xs capitalize ${isLight ? "text-slate-600" : "text-slate-300"}`}>
          {detection.object_class.replaceAll("_", " ")}
        </div>

        {/* Confidence Progress Meter */}
        <div className="mt-3">
          <div className="flex justify-between text-xs mb-1">
            <span className={isLight ? "text-slate-500" : "text-slate-400"}>AI Confidence:</span>
            <span className={`font-bold ${isActionable ? "text-emerald-500" : "text-amber-500"}`}>
              {(detection.confidence * 100).toFixed(1)}%
              {isActionable ? " (Actionable Alert)" : " (Requires Human Review)"}
            </span>
          </div>
          <div className={`h-2 w-full rounded-full overflow-hidden ${isLight ? "bg-slate-200" : "bg-slate-800"}`}>
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
          <div className={`rounded-lg border p-2.5 ${isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-800/40"}`}>
            <div className={`text-[10px] uppercase ${isLight ? "text-slate-500" : "text-slate-400"}`}>Latitude / Longitude</div>
            <div className={`mt-0.5 font-semibold ${isLight ? "text-slate-900" : "text-slate-200"}`}>
              {detection.latitude.toFixed(4)}°N, {detection.longitude.toFixed(4)}°E
            </div>
          </div>
          <div className={`rounded-lg border p-2.5 ${isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-800/40"}`}>
            <div className={`text-[10px] uppercase ${isLight ? "text-slate-500" : "text-slate-400"}`}>Estimated Area</div>
            <div className={`mt-0.5 font-semibold ${isLight ? "text-slate-900" : "text-slate-200"}`}>
              {detection.area_m2 ? `${detection.area_m2.toFixed(1)} m²` : "Point Target"}
            </div>
          </div>
          <div className={`rounded-lg border p-2.5 ${isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-800/40"}`}>
            <div className={`text-[10px] uppercase ${isLight ? "text-slate-500" : "text-slate-400"}`}>Detection Sensor</div>
            <div className={`mt-0.5 font-semibold capitalize ${isLight ? "text-slate-900" : "text-slate-200"}`}>{detection.source}</div>
          </div>
          <div className={`rounded-lg border p-2.5 ${isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-800/40"}`}>
            <div className={`text-[10px] uppercase ${isLight ? "text-slate-500" : "text-slate-400"}`}>Observation Time</div>
            <div className={`mt-0.5 font-semibold ${isLight ? "text-slate-900" : "text-slate-200"}`}>
              {new Date(detection.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC
            </div>
          </div>
        </div>

        {/* Incident Assignment Banner */}
        {detection.assigned_team && (
          <div className={`rounded-xl border p-3 text-xs ${
            isLight ? "border-sky-200 bg-sky-50/70 text-slate-800" : "border-sky-500/30 bg-sky-950/30 text-slate-100"
          }`}>
            <div className={`font-semibold ${isLight ? "text-sky-700" : "text-sky-300"}`}>Assigned Response Team:</div>
            <div className={`font-bold ${isLight ? "text-slate-900" : "text-slate-100"}`}>{detection.assigned_team}</div>
            {detection.assigned_to && (
              <div className={`text-[11px] ${isLight ? "text-slate-600" : "text-slate-400"}`}>Lead: {detection.assigned_to}</div>
            )}
            {detection.verification_notes && (
              <div className={`mt-1.5 italic text-[11px] border-t pt-1 ${
                isLight ? "border-sky-200 text-slate-700" : "border-sky-900/50 text-slate-300"
              }`}>
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
              className={`rounded-xl border px-3 py-2 text-xs font-bold transition ${
                isLight
                  ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
              }`}
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
            <div className={`rounded-xl border p-3.5 ${
              isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-900/60"
            }`}>
              <div className={`flex items-center justify-between border-b pb-2 ${isLight ? "border-slate-200" : "border-slate-800"}`}>
                <span className={`text-xs font-bold uppercase tracking-wider ${isLight ? "text-amber-700" : "text-yellow-400"}`}>
                  Drift Agent Ensemble (OpenDrift)
                </span>
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                  isLight ? "bg-amber-100 text-amber-800 border border-amber-200" : "bg-yellow-400/10 text-yellow-300"
                }`}>
                  {analysis.drift.mode.toUpperCase()}
                </span>
              </div>
              <div className="mt-2.5 space-y-1.5">
                {analysis.drift.horizons.map((h) => (
                  <div key={h.forecast_hour} className="flex justify-between text-xs">
                    <span className={`font-semibold ${isLight ? "text-slate-700" : "text-slate-300"}`}>+{h.forecast_hour}h Horizon:</span>
                    <span className={isLight ? "text-slate-600" : "text-slate-400"}>
                      {h.mean_latitude.toFixed(3)}°N, {h.mean_longitude.toFixed(3)}°E
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Ecological Risk & Priority */}
            <div className={`rounded-xl border p-3.5 ${
              isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-900/60"
            }`}>
              <div className={`flex items-center justify-between border-b pb-2 ${isLight ? "border-slate-200" : "border-slate-800"}`}>
                <span className={`text-xs font-bold uppercase tracking-wider ${isLight ? "text-rose-700" : "text-rose-400"}`}>
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
                  <span className={isLight ? "text-slate-500" : "text-slate-400"}>Protected Area Overlap:</span>
                  <span className={analysis.geospatial.protected_area_overlap ? "text-rose-600 font-bold" : isLight ? "text-slate-700" : "text-slate-300"}>
                    {analysis.geospatial.protected_area_overlap ? "YES (Threat Confirmed)" : "None"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className={isLight ? "text-slate-500" : "text-slate-400"}>Coral Reef / Habitat Proximity:</span>
                  <span className={analysis.geospatial.habitat_overlap ? "text-rose-600 font-bold" : isLight ? "text-slate-700" : "text-slate-300"}>
                    {analysis.geospatial.habitat_overlap ? "YES" : `${analysis.geospatial.distance_to_nearest_protected_area_km.toFixed(1)} km`}
                  </span>
                </div>
                {analysis.geospatial.nearest_protected_area && (
                  <div className={`text-[11px] pt-1 ${isLight ? "text-slate-700" : "text-slate-300"}`}>
                    Nearest Ecological Zone: <strong>{analysis.geospatial.nearest_protected_area}</strong>
                  </div>
                )}
              </div>
            </div>

            {/* AI Synthesized Intelligence Report */}
            <div className={`rounded-xl border p-3.5 ${
              isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-900/60"
            }`}>
              <div className={`text-xs font-bold uppercase tracking-wider mb-1.5 ${isLight ? "text-sky-700" : "text-sky-400"}`}>
                RAG & Evidence Agent Synthesis
              </div>
              <p className={`text-xs leading-relaxed ${isLight ? "text-slate-700" : "text-slate-200"}`}>{analysis.report.summary}</p>

              {analysis.report.evidence.length > 0 && (
                <div className={`mt-3 space-y-2 border-t pt-2 ${isLight ? "border-slate-200" : "border-slate-800"}`}>
                  <div className={`text-[10px] uppercase font-bold ${isLight ? "text-slate-500" : "text-slate-400"}`}>Cited Literature & Data Provenance</div>
                  {analysis.report.evidence.map((e, idx) => (
                    <div key={idx} className={`rounded p-2 text-[11px] ${
                      isLight ? "bg-white border border-slate-200 text-slate-700" : "bg-slate-950/70 text-slate-300"
                    }`}>
                      <div className={`text-[9px] uppercase font-bold ${isLight ? "text-sky-700" : "text-sky-400"}`}>{e.source}</div>
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
