"use client";

interface LayerToggleProps {
  visibleLayers: Record<string, boolean>;
  onToggle: (key: string) => void;
  onOpenDataSources: () => void;
}

interface LayerItem {
  key: string;
  label: string;
  badge: string;
  color: string;
}

const LAYERS: LayerItem[] = [
  { key: "detections", label: "Debris Detections", badge: "AI / SAR", color: "bg-red-500" },
  { key: "trajectories", label: "Drift Cones (24h/48h/72h)", badge: "OpenDrift", color: "bg-yellow-400" },
  { key: "coralReefs", label: "Coral Reefs", badge: "UNEP-WCMC", color: "bg-cyan-400" },
  { key: "speciesHabitats", label: "Marine Life Habitats", badge: "SWOT/OBIS", color: "bg-purple-400" },
  { key: "protectedAreas", label: "Marine Protected Areas", badge: "WDPA", color: "bg-emerald-400" },
  { key: "riskZones", label: "High Risk Polygons", badge: "Risk Agent", color: "bg-rose-500" },
  { key: "ecologicalAlerts", label: "Ecological Alert Pins", badge: "Live Threat", color: "bg-orange-500" },
];

export default function LayerToggle({ visibleLayers, onToggle, onOpenDataSources }: LayerToggleProps) {
  return (
    <div className="pointer-events-auto w-64 rounded-xl border border-sky-500/20 bg-slate-950/90 p-3.5 text-xs shadow-xl backdrop-blur-md">
      <div className="mb-2.5 flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="font-bold uppercase tracking-wider text-slate-300 text-[11px]">
          Operational Layers
        </span>
        <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-sky-400">
          Interactive
        </span>
      </div>

      <div className="space-y-1.5">
        {LAYERS.map((layer) => {
          const isChecked = visibleLayers[layer.key] ?? true;
          return (
            <label
              key={layer.key}
              className="flex cursor-pointer items-center justify-between rounded-lg p-1.5 transition hover:bg-slate-900/60"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => onToggle(layer.key)}
                  className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-sky-500 accent-sky-500 focus:ring-0"
                />
                <span className={`inline-block h-2 w-2 rounded-full ${layer.color}`} />
                <span className={`text-[11px] font-medium ${isChecked ? "text-slate-200" : "text-slate-500"}`}>
                  {layer.label}
                </span>
              </div>
              <span className="text-[9px] text-slate-500">{layer.badge}</span>
            </label>
          );
        })}
      </div>

      <div className="mt-3 border-t border-slate-800/80 pt-2 flex items-center justify-between">
        <button
          onClick={onOpenDataSources}
          className="text-[10px] text-sky-400 hover:text-sky-300 underline font-medium"
        >
          View Scientific Data Sources ↗
        </button>
      </div>
    </div>
  );
}
