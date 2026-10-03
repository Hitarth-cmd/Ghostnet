"use client";

import type { Detection, EcologicalAlert } from "@/types";

interface StatsBarProps {
  detections: Detection[];
  ecologicalAlerts?: EcologicalAlert[];
  onOpenResponderPortal: () => void;
  onOpenDataSources: () => void;
}

export default function StatsBar({
  detections,
  ecologicalAlerts = [],
  onOpenResponderPortal,
  onOpenDataSources,
}: StatsBarProps) {
  const total = detections.length;
  const actionable = detections.filter((d) => d.confidence >= 0.70).length;
  const awaitingVerification = detections.filter(
    (d) => d.confidence < 0.70 && (d.incident_status === "unverified" || d.status === "unverified")
  ).length;
  const activeAlerts = ecologicalAlerts.filter((a) => a.status === "active").length;

  return (
    <div className="pointer-events-auto flex items-center gap-4 rounded-xl border border-sky-500/20 bg-slate-950/90 px-4 py-2 shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-5 border-r border-slate-800 pr-4">
        <div className="text-center">
          <div className="text-base font-bold text-slate-100">{total}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">Total Detections</div>
        </div>

        <div className="text-center">
          <div className="text-base font-bold text-orange-400">{actionable}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-orange-300">Cleanup Alerts (&ge;70%)</div>
        </div>

        <div className="text-center">
          <div className="text-base font-bold text-amber-400">{awaitingVerification}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-amber-300">Review Queue (&lt;70%)</div>
        </div>

        <div className="text-center">
          <div className="text-base font-bold text-rose-400">{activeAlerts}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-rose-300">Active Habitat Threats</div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenResponderPortal}
          className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-md transition hover:from-sky-500 hover:to-indigo-500 hover:shadow-sky-500/25"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          Admin &amp; Responder Login
        </button>

        <button
          onClick={onOpenDataSources}
          className="rounded-lg border border-slate-800 bg-slate-900/90 px-2.5 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
          title="Inspect Autonomous Scientific Data Layers"
        >
          Data Provenance ↗
        </button>
      </div>
    </div>
  );
}
