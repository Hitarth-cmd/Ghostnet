"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface DataSourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
  theme?: "light" | "dark";
}

export default function DataSourcesModal({ isOpen, onClose, theme = "light" }: DataSourcesModalProps) {
  const isLight = theme === "light";
  const [layers, setLayers] = useState<any[]>([]);

  useEffect(() => {
    if (isOpen) {
      api.mapLayersMetadata().then((res) => setLayers(res.layers || [])).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const realSources = [
    {
      title: "Marine Protected Areas (WDPA)",
      organization: "UNEP-WCMC & IUCN Protected Planet",
      coverage: "Indian Ocean, Arabian Sea, Bay of Bengal, Lakshadweep, Andamans",
      license: "CC-BY 3.0 IGO",
      url: "https://www.protectedplanet.net",
      description: "Official World Database on Protected Areas defining national marine parks, wildlife sanctuaries, and biosphere reserves.",
      cachedFile: "backend/data/cached_mpas.geojson",
    },
    {
      title: "Global Distribution of Coral Reefs (WCMC 008)",
      organization: "UNEP-WCMC / Global Coral Reef Monitoring Network (GCRMN)",
      coverage: "Gulf of Mannar, Lakshadweep Atolls, Andaman & Nicobar, Malvan, Gulf of Kutch",
      license: "WCMC Data Licence / CC BY 4.0",
      url: "https://data.unep-wcmc.org/datasets/1",
      description: "Validated high-resolution shallow-water coral reef polygons representing biologically fragile calcifying ecosystems.",
      cachedFile: "backend/data/cached_coral_reefs.geojson",
    },
    {
      title: "Marine Megafauna & Sea Turtle Nesting Grounds (SWOT / OBIS-SEAMAP)",
      organization: "State of the World's Sea Turtles (SWOT) & Duke University",
      coverage: "Odisha (Gahirmatha/Rushikulya Olive Ridley), Lakshadweep (Spinner Dolphins), Gujarat (Whale Sharks), Tamil Nadu (Dugongs)",
      license: "OBIS Open Access / Creative Commons",
      url: "https://seamap.env.duke.edu",
      description: "Scientific telemetry, nesting rookeries, and congregation corridors for IUCN Red List threatened marine species.",
      cachedFile: "backend/data/cached_species_habitats.geojson",
    },
    {
      title: "High-Resolution Coastlines (GSHHG)",
      organization: "NOAA National Centers for Environmental Information",
      coverage: "Global Continental & Island Shorelines",
      license: "Public Domain / LGPL",
      url: "https://www.ngdc.noaa.gov/mgg/shorelines/gshhs.html",
      description: "Hierarchical high-resolution vector coastline dataset used for beaching calculations and distance-to-shore risk modeling.",
      cachedFile: "backend/data/demo_coastline.geojson",
    },
    {
      title: "Ocean Surface Currents & Hydrodynamic Forcing",
      organization: "Copernicus Marine Service (E.U. CMEMS) & INCOIS",
      coverage: "Global & Northern Indian Ocean Basin (0.083° Physical Analysis & Forecast)",
      license: "E.U. Copernicus Marine Open Data / CC-BY",
      url: "https://marine.copernicus.eu",
      description: "Real-time surface velocity fields (uo, vo variables at 0.5m depth) driving 60fps WebGL particle streamlines and Lagrangian drift forecasts.",
      cachedFile: "backend/data/cached_cmems_currents.json",
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-md">
      <div className={`relative flex h-[80vh] w-full max-w-4xl flex-col rounded-2xl border shadow-2xl transition-colors ${
        isLight
          ? "border-slate-200/90 bg-white/98 text-slate-800 shadow-slate-900/15"
          : "border-sky-500/20 bg-slate-950/95 text-slate-100"
      }`}>
        <div className={`flex items-center justify-between border-b px-6 py-4 ${
          isLight ? "border-slate-200 bg-slate-50/80" : "border-slate-800"
        }`}>
          <div className="flex items-center gap-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
              isLight ? "bg-emerald-100 text-emerald-700" : "bg-emerald-500/20 text-emerald-400"
            }`}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <h2 className={`text-base font-bold ${isLight ? "text-slate-900" : "text-slate-100"}`}>
                Data Provenance & Autonomous Environmental Datasets
              </h2>
              <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                Peer-reviewed, transparent, and locally cached scientific datasets powering ecological alerts
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`rounded-lg p-1.5 transition ${
              isLight ? "text-slate-400 hover:bg-slate-100 hover:text-slate-700" : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          <div className={`rounded-lg border p-3 text-xs ${
            isLight
              ? "border-sky-200 bg-sky-50 text-sky-900"
              : "border-sky-500/20 bg-sky-950/20 text-sky-200"
          }`}>
            <strong>Authentic Geospatial Policy:</strong> OceanGuard does not synthesize or fabricate ecological facts.
            All marine protected boundaries, reef contours, and endangered species nesting grounds are collected from international organizations, verified, and cached locally in the backend for deterministic spatial reasoning.
          </div>

          <div className="grid gap-4">
            {realSources.map((s, idx) => (
              <div key={idx} className={`rounded-xl border p-4 ${
                isLight
                  ? "border-slate-200 bg-slate-50/70"
                  : "border-slate-800 bg-slate-900/60"
              }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className={`font-bold text-sm ${isLight ? "text-slate-900" : "text-slate-100"}`}>{s.title}</h3>
                    <div className={`mt-0.5 text-xs font-medium ${isLight ? "text-emerald-600" : "text-emerald-400"}`}>{s.organization}</div>
                  </div>
                  <span className={`rounded border px-2 py-0.5 text-[10px] ${
                    isLight
                      ? "border-slate-200 bg-white text-slate-600"
                      : "border-slate-700 bg-slate-800 text-slate-300"
                  }`}>
                    License: {s.license}
                  </span>
                </div>

                <p className={`mt-2 text-xs leading-relaxed ${isLight ? "text-slate-600" : "text-slate-300"}`}>{s.description}</p>

                <div className={`mt-3 flex flex-wrap items-center gap-4 text-[11px] border-t pt-2.5 ${
                  isLight ? "border-slate-200 text-slate-500" : "border-slate-800/80 text-slate-400"
                }`}>
                  <div>Coverage: <span className={isLight ? "font-medium text-slate-700" : "text-slate-200"}>{s.coverage}</span></div>
                  <div>Cache: <code className={isLight ? "text-sky-700 font-semibold" : "text-sky-300"}>{s.cachedFile}</code></div>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className={`ml-auto underline font-medium ${isLight ? "text-sky-600 hover:text-sky-800" : "text-sky-400 hover:text-sky-300"}`}
                  >
                    Dataset Documentation &rarr;
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={`flex justify-end border-t px-6 py-3 ${
          isLight ? "border-slate-200 bg-slate-50/50" : "border-slate-800"
        }`}>
          <button
            onClick={onClose}
            className={`rounded-lg px-4 py-2 text-xs font-medium transition ${
              isLight
                ? "bg-slate-200 text-slate-800 hover:bg-slate-300"
                : "bg-slate-800 text-slate-200 hover:bg-slate-700"
            }`}
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
