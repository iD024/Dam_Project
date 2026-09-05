"use client";

import React from "react";
import { Users, AlertTriangle, ShieldAlert, Navigation, Home, Activity } from "lucide-react";
import { ImpactData } from "@/lib/api";

interface ImpactPanelProps {
  impact?: ImpactData | null;
  onFocusVillage: (coords: [number, number]) => void;
}

export default function ImpactPanel({ impact, onFocusVillage }: ImpactPanelProps) {
  if (!impact) {
    return (
      <div className="p-6 text-center text-slate-400 text-xs flex flex-col items-center justify-center h-full">
        <Activity className="w-8 h-8 text-slate-600 mb-2 animate-pulse" />
        <p className="font-semibold text-slate-300">No Active Simulation Impact</p>
        <p className="text-[11px] mt-1">Run a hydrodynamic simulation to inspect settlement impact analytics.</p>
      </div>
    );
  }

  // Village coordinate mapping for Tehri Basin
  const villageCoords: Record<string, [number, number]> = {
    "Koti Colony": [78.4720, 30.3650],
    "Malidewal": [78.4950, 30.3400],
    "Khand": [78.5300, 30.2950],
    "Chhiddarwala": [78.5600, 30.2400],
    "Devprayag": [78.5980, 30.1450],
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200 w-96 p-5 overflow-y-auto">
      {/* Header */}
      <div className="pb-3 border-b border-slate-800">
        <h2 className="font-bold text-lg text-white flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          Spatial Impact Assessment
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">PostGIS Exposure & Settlement Intersections</p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 gap-2.5 mt-4">
        <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
          <div className="text-[10px] text-slate-400 uppercase font-medium">Peak Inundation</div>
          <div className="text-xl font-bold text-sky-400 font-mono mt-0.5">{impact.peak_flood_area_km2} <span className="text-xs font-normal text-slate-400">km²</span></div>
        </div>

        <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
          <div className="text-[10px] text-slate-400 uppercase font-medium">Max Water Depth</div>
          <div className="text-xl font-bold text-indigo-400 font-mono mt-0.5">{impact.max_depth_m} <span className="text-xs font-normal text-slate-400">m</span></div>
        </div>

        <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
          <div className="text-[10px] text-slate-400 uppercase font-medium">Peak Flow Velocity</div>
          <div className="text-xl font-bold text-amber-400 font-mono mt-0.5">{impact.max_velocity_ms} <span className="text-xs font-normal text-slate-400">m/s</span></div>
        </div>

        <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
          <div className="text-[10px] text-slate-400 uppercase font-medium">Earliest Arrival</div>
          <div className="text-xl font-bold text-rose-400 font-mono mt-0.5">{impact.earliest_arrival_min} <span className="text-xs font-normal text-slate-400">min</span></div>
        </div>
      </div>

      {/* Infrastructure Cutoffs */}
      <div className="mt-4 p-3 rounded-xl bg-slate-800/40 border border-slate-700/60 text-xs">
        <div className="font-semibold text-slate-300 mb-2 flex items-center justify-between">
          <span>Inundated Lifelines & Infrastructure</span>
          <span className="text-[10px] text-rose-400">High HADR Priority</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-slate-300">
          <div>Roads Cut Off: <span className="text-white font-semibold font-mono">{impact.affected_roads_km} km</span></div>
          <div>Bridges Submerged: <span className="text-white font-semibold font-mono">{impact.affected_bridges_count}</span></div>
          <div>Hospitals at Risk: <span className="text-white font-semibold font-mono">{impact.affected_hospitals_count}</span></div>
          <div>Schools at Risk: <span className="text-white font-semibold font-mono">{impact.affected_schools_count}</span></div>
        </div>
      </div>

      {/* Affected Settlements List */}
      <div className="mt-5 flex-1">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-xs text-slate-300 flex items-center gap-1.5">
            <Users className="w-4 h-4 text-sky-400" />
            Inundated Settlements ({impact.affected_villages.length})
          </h3>
          <span className="text-[10px] text-slate-500">Click to locate</span>
        </div>

        <div className="space-y-2">
          {impact.affected_villages.map((v, i) => {
            const coords = villageCoords[v.name] || [78.53, 30.28];
            const isCrit = v.risk_level === "CRITICAL";
            return (
              <div
                key={i}
                onClick={() => onFocusVillage(coords)}
                className="p-3 rounded-xl bg-slate-800/80 hover:bg-slate-750 border border-slate-700/80 cursor-pointer transition flex items-center justify-between group"
              >
                <div>
                  <div className="font-semibold text-sm text-white group-hover:text-sky-400 transition flex items-center gap-1.5">
                    {v.name}
                    <Navigation className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition" />
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-3">
                    <span>Arrival: <strong className="text-slate-200">{v.arrival_time_min}m</strong></span>
                    <span>Depth: <strong className="text-slate-200">{v.max_depth_m}m</strong></span>
                    <span>Pop: <strong className="text-slate-200">{v.population_est}</strong></span>
                  </div>
                </div>

                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  isCrit
                    ? "bg-rose-950 text-rose-400 border-rose-800/60"
                    : "bg-amber-950 text-amber-400 border-amber-800/60"
                }`}>
                  {v.risk_level}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hazard Depth Zonation */}
      <div className="mt-5 pt-4 border-t border-slate-800 text-xs space-y-2">
        <div className="font-semibold text-slate-300">Hazard Depth Classification</div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between items-center text-slate-300">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#38bdf8]" /> Low (&lt; 0.5m)</span>
            <span className="font-mono text-slate-400">{impact.hazard_zones_km2?.low_lt_0_5m_km2 || 0} km²</span>
          </div>
          <div className="flex justify-between items-center text-slate-300">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#0284c7]" /> Medium (0.5 - 1.5m)</span>
            <span className="font-mono text-slate-400">{impact.hazard_zones_km2?.medium_0_5_to_1_5m_km2 || 0} km²</span>
          </div>
          <div className="flex justify-between items-center text-slate-300">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#1e40af]" /> High (1.5 - 3.0m)</span>
            <span className="font-mono text-slate-400">{impact.hazard_zones_km2?.high_1_5_to_3_0m_km2 || 0} km²</span>
          </div>
          <div className="flex justify-between items-center text-slate-300">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#312e81]" /> Extreme (&gt; 3.0m)</span>
            <span className="font-mono text-slate-400">{impact.hazard_zones_km2?.extreme_gt_3_0m_km2 || 0} km²</span>
          </div>
        </div>
      </div>
    </div>
  );
}
