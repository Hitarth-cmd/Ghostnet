"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface DataSourcesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DataSourcesModal({ isOpen, onClose }: DataSourcesModalProps) {
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
      title: "Ocean Surface Currents & Drift Forcing",
      organization: "INCOIS (Indian National Centre for Ocean Information Services) & OpenDrift",
      coverage: "Northern Indian Ocean (5°S–25°N, 60°E–100°E)",
      license: "INCOIS Open Data / OpenDrift (GPL-2.0)",
      url: "https://incois.gov.in / https://opendrift.github.io",
      description: "Lagrangian particle drift trajectory simulator driven by ocean current vectors and windage factors (24h, 48h, 72h horizons).",
      cachedFile: "backend/data/currents_grid.zarr",
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-md">
      <div className="relative flex h-[80vh] w-full max-w-4xl flex-col rounded-2xl border border-sky-500/20 bg-slate-950/95 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                Data Provenance & Autonomous Environmental Datasets
              </h2>
              <p className="text-xs text-slate-400">
                Peer-reviewed, transparent, and locally cached scientific datasets powering ecological alerts
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          <div className="rounded-lg border border-sky-500/20 bg-sky-950/20 p-3 text-xs text-sky-200">
            <strong>Authentic Geospatial Policy:</strong> OceanGuard does not synthesize or fabricate ecological facts.
            All marine protected boundaries, reef contours, and endangered species nesting grounds are collected from international organizations, verified, and cached locally in the backend for deterministic spatial reasoning.
          </div>

          <div className="grid gap-4">
            {realSources.map((s, idx) => (
              <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-slate-100 text-sm">{s.title}</h3>
                    <div className="mt-0.5 text-xs text-emerald-400 font-medium">{s.organization}</div>
                  </div>
                  <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                    License: {s.license}
                  </span>
                </div>

                <p className="mt-2 text-xs text-slate-300">{s.description}</p>

                <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-slate-400 border-t border-slate-800/80 pt-2.5">
                  <div>Coverage: <span className="text-slate-200">{s.coverage}</span></div>
                  <div>Cache: <code className="text-sky-300">{s.cachedFile}</code></div>
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto text-sky-400 hover:text-sky-300 underline"
                  >
                    Dataset Documentation &rarr;
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end border-t border-slate-800 px-6 py-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
