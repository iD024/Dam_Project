"use client";

import React from "react";
import { Eye, Layers, Gauge, Clock, Satellite } from "lucide-react";

interface LayerControlProps {
  activeLayer: "depth" | "velocity" | "arrival" | "none";
  onSelectLayer: (layer: "depth" | "velocity" | "arrival" | "none") => void;
  showSatelliteObserved: boolean;
  onToggleSatellite: (show: boolean) => void;
}

export default function LayerControlPanel({
  activeLayer,
  onSelectLayer,
  showSatelliteObserved,
  onToggleSatellite,
}: LayerControlProps) {
  return (
    <div className="absolute top-4 left-4 z-20 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl p-3.5 shadow-2xl text-xs text-slate-200 w-60 space-y-3">
      <div className="font-semibold text-white flex items-center justify-between border-b border-slate-800 pb-2">
        <span className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-sky-400" />
          Map Layers & Ramp
        </span>
      </div>

      {/* Layer Selection Buttons */}
      <div className="space-y-1.5">
        <button
          onClick={() => onSelectLayer("depth")}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition ${
            activeLayer === "depth"
              ? "bg-sky-600/30 border-sky-500 text-sky-300 font-semibold"
              : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-750"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
            Water Depth (m)
          </span>
          <span className="text-[10px] font-mono text-slate-400">0 - 8m</span>
        </button>

        <button
          onClick={() => onSelectLayer("velocity")}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition ${
            activeLayer === "velocity"
              ? "bg-amber-600/30 border-amber-500 text-amber-300 font-semibold"
              : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-750"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            Flow Velocity (m/s)
          </span>
          <span className="text-[10px] font-mono text-slate-400">0 - 6 m/s</span>
        </button>

        <button
          onClick={() => onSelectLayer("arrival")}
          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition ${
            activeLayer === "arrival"
              ? "bg-emerald-600/30 border-emerald-500 text-emerald-300 font-semibold"
              : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-750"
          }`}
        >
          <span className="flex items-center gap-1.5">
            <Clock className="w-2.5 h-2.5 text-emerald-400" />
            Arrival Isochrones
          </span>
          <span className="text-[10px] font-mono text-slate-400">0 - 60 min</span>
        </button>
      </div>

      {/* Satellite Observed Layer Checkbox */}
      <div className="pt-2 border-t border-slate-800">
        <label className="flex items-center justify-between cursor-pointer group">
          <span className="flex items-center gap-1.5 text-slate-300 group-hover:text-white">
            <Satellite className="w-3.5 h-3.5 text-fuchsia-400" />
            Sentinel-1 SAR
          </span>
          <input
            type="checkbox"
            checked={showSatelliteObserved}
            onChange={(e) => onToggleSatellite(e.target.checked)}
            className="rounded bg-slate-800 border-slate-700 text-fuchsia-600 focus:ring-0 cursor-pointer"
          />
        </label>
      </div>

      {/* Dynamic Color Ramp Legend */}
      <div className="pt-2 border-t border-slate-800 space-y-1">
        <div className="text-[10px] text-slate-400 font-medium">
          {activeLayer === "velocity" ? "Velocity Ramp (m/s)" : activeLayer === "arrival" ? "Arrival Time (min)" : "Water Depth Ramp (m)"}
        </div>
        <div className="h-2 rounded-full overflow-hidden flex">
          {activeLayer === "velocity" ? (
            <>
              <div className="flex-1 bg-[#fef08a]" />
              <div className="flex-1 bg-[#f97316]" />
              <div className="flex-1 bg-[#dc2626]" />
              <div className="flex-1 bg-[#7f1d1d]" />
            </>
          ) : activeLayer === "arrival" ? (
            <>
              <div className="flex-1 bg-[#86efac]" />
              <div className="flex-1 bg-[#eab308]" />
              <div className="flex-1 bg-[#f97316]" />
              <div className="flex-1 bg-[#ef4444]" />
            </>
          ) : (
            <>
              <div className="flex-1 bg-[#38bdf8]" />
              <div className="flex-1 bg-[#0284c7]" />
              <div className="flex-1 bg-[#1e40af]" />
              <div className="flex-1 bg-[#312e81]" />
            </>
          )}
        </div>
        <div className="flex justify-between text-[9px] text-slate-400 font-mono">
          <span>Low</span>
          <span>Moderate</span>
          <span>Critical</span>
        </div>
      </div>
    </div>
  );
}
