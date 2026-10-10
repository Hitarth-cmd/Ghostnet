"use client";

import { useEffect, useState } from "react";
import type { EcologicalAlert } from "@/types";

interface EcologicalAlertBannerProps {
  alerts: EcologicalAlert[];
  onSelectAlert: (externalId: string) => void;
  onOpenResponderPortal: () => void;
  theme?: "light" | "dark";
}

export default function EcologicalAlertBanner({
  alerts,
  onSelectAlert,
  onOpenResponderPortal,
  theme = "light",
}: EcologicalAlertBannerProps) {
  const isLight = theme === "light";
  const [currentIndex, setCurrentIndex] = useState(0);
  const activeAlerts = alerts.filter(
    (a) => a.status === "active" && (a.severity === "CRITICAL" || a.severity === "HIGH")
  );

  // Auto-rotate ticker if multiple alerts exist
  useEffect(() => {
    if (activeAlerts.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % activeAlerts.length);
    }, 6000);
    return () => clearInterval(timer);
  }, [activeAlerts.length]);

  if (activeAlerts.length === 0) return null;

  const current = activeAlerts[currentIndex % activeAlerts.length];

  return (
    <div className={`relative mx-auto flex w-full max-w-xl items-center justify-between rounded-xl border px-3 py-1.5 text-xs shadow-2xl backdrop-blur-md transition-colors ${
      isLight
        ? "border-rose-300/90 bg-white/95 text-slate-800 shadow-rose-900/10"
        : "border-rose-500/40 bg-slate-950/90 text-slate-200"
    }`}>
      <div className="flex items-center gap-3 overflow-hidden">
        <span className="relative flex h-3 w-3 shrink-0">
          <span className="live-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500" />
        </span>

        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold tracking-wider ${
            current.severity === "CRITICAL"
              ? "bg-rose-600 text-white"
              : "bg-orange-500 text-white"
          }`}
        >
          {current.severity} ECOLOGICAL THREAT
        </span>

        <div className={`truncate ${isLight ? "text-slate-800" : "text-slate-200"}`}>
          <strong className={isLight ? "text-slate-900" : "text-slate-100"}>{current.region_name}:</strong>{" "}
          <span>{current.headline}</span>
          <span className={`ml-2 ${isLight ? "text-slate-500" : "text-slate-400"}`}>
            (~{current.distance_km.toFixed(1)} km, ETA {current.estimated_impact_hours.toFixed(1)}h)
          </span>
        </div>
      </div>

      <div className="ml-3 flex shrink-0 items-center gap-2">
        <button
          onClick={() => onSelectAlert(current.external_id)}
          className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
            isLight
              ? "border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100"
              : "border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
          }`}
        >
          Locate ↗
        </button>
        <button
          onClick={onOpenResponderPortal}
          className="rounded-lg bg-sky-600 px-2.5 py-1 text-[11px] font-semibold text-white transition hover:bg-sky-500"
        >
          Intervene
        </button>

        {activeAlerts.length > 1 && (
          <span className={`text-[10px] ${isLight ? "text-slate-500" : "text-slate-500"}`}>
            {currentIndex + 1}/{activeAlerts.length}
          </span>
        )}
      </div>
    </div>
  );
}
