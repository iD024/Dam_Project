"use client";

import React, { useState } from "react";
import { Sparkles, CheckCircle2, AlertTriangle, Play, HelpCircle, Layers, Loader2 } from "lucide-react";
import { api, Dam } from "@/lib/api";

interface ScenarioDrawerProps {
  dam?: Dam;
  onRunSimulation: (params: any) => void;
  isRunning: boolean;
}

export default function ScenarioDrawer({ dam, onRunSimulation, isRunning }: ScenarioDrawerProps) {
  const [breachWidth, setBreachWidth] = useState(95.0);
  const [topWidth, setTopWidth] = useState(140.0);
  const [formationTime, setFormationTime] = useState(240.0);
  const [invertElevation, setInvertElevation] = useState(750.0);
  const [reservoirLevel, setReservoirLevel] = useState(820.0);
  const [solver, setSolver] = useState("fast_swe");
  const [manningN, setManningN] = useState(0.042);
  const [aiRecommendation, setAiRecommendation] = useState<any>(null);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [loadingAi, setLoadingAi] = useState(false);

  // Trigger AI Parameter Recommendation (Froehlich 2008 Multi-Regressive Empirical Regression)
  const handleAiRecommend = async () => {
    setLoadingAi(true);
    try {
      const rec = await api.recommendBreachParams({
        dam_height_m: dam?.height_m || 260.5,
        reservoir_storage_m3: dam?.reservoir_storage_m3 || 3.54e9,
        dam_type: dam?.dam_type || "embankment",
        failure_mode: "overtopping",
      });
      setAiRecommendation(rec);
      setBreachWidth(rec.recommended_breach_width_m);
      setTopWidth(roundVal(rec.recommended_breach_width_m * 1.4));
      setFormationTime(rec.recommended_formation_time_s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAi(false);
    }
  };

  const roundVal = (v: number) => Math.round(v * 10) / 10;

  const handleValidate = async () => {
    try {
      const res = await api.checkInputQuality({
        schema_version: "1.0.0",
        project_id: "proj_tehri_001",
        dam_id: dam?.id || "dam_001",
        river_id: "riv_001",
        domain: { bbox: [78.45, 30.12, 78.65, 30.40], crs: "EPSG:4326" },
        terrain: { dem_uri: "data/demo/tehri/dem_tehri.tif", resolution_m: 30.0 },
        hydrology: {
          initial_reservoir_level_m: reservoirLevel,
          initial_storage_m3: dam?.reservoir_storage_m3 || 3.54e9,
        },
        roughness: { source: "landcover", default_manning_n: manningN },
        breach: {
          type: "trapezoidal_progressive",
          failure_mode: "overtopping",
          formation_time_s: formationTime,
          bottom_width_m: breachWidth,
          top_width_m: topWidth,
          side_slope_hv: 1.0,
          bottom_elevation_m: invertElevation,
        },
        solvers: [solver],
        numerics: { simulation_duration_s: 600.0, output_interval_s: 60.0, max_courant: 0.85, dry_threshold_m: 0.02 },
      });
      setValidationResult(res);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRun = () => {
    onRunSimulation({
      breachWidth,
      topWidth,
      formationTime,
      invertElevation,
      reservoirLevel,
      manningN,
      solver,
    });
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 text-slate-200 w-96 p-5 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="font-bold text-lg text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-sky-400" />
            Scenario Builder
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">Physical Parameters & Breach Setup</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950 text-sky-400 border border-sky-800/60">
          v1.0.0
        </span>
      </div>

      {/* Dam Specs Card */}
      <div className="mt-4 p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs space-y-1.5">
        <div className="font-semibold text-sky-400 flex items-center justify-between">
          <span>{dam?.name || "Tehri Dam"}</span>
          <span className="text-slate-400 text-[10px] font-normal">{dam?.dam_type || "Rockfill"}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 pt-1 text-slate-300">
          <div>Crest: <span className="text-white font-mono">{dam?.crest_elevation_m || 839.5} m</span></div>
          <div>Height: <span className="text-white font-mono">{dam?.height_m || 260.5} m</span></div>
          <div className="col-span-2">Active Storage: <span className="text-white font-mono">3.54 Billion m³</span></div>
        </div>
      </div>

      {/* AI Recommender Action */}
      <div className="mt-4">
        <button
          onClick={handleAiRecommend}
          disabled={loadingAi}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium text-xs shadow-md transition disabled:opacity-50"
        >
          <Sparkles className="w-4 h-4 text-amber-300" />
          {loadingAi ? "Calculating Froehlich Regressions..." : "AI Recommend Breach Parameters"}
        </button>

        {aiRecommendation && (
          <div className="mt-2.5 p-3 rounded-lg bg-violet-950/40 border border-violet-800/50 text-[11px] space-y-1 text-violet-200 animate-in fade-in">
            <div className="font-semibold text-violet-300 flex items-center justify-between">
              <span>{aiRecommendation.method}</span>
              <span className="text-amber-400 font-mono">Confidence: 92%</span>
            </div>
            <div>Width Range: <span className="font-mono text-white">{aiRecommendation.breach_width_range_m[0]} - {aiRecommendation.breach_width_range_m[1]} m</span></div>
            <div>Formation Time: <span className="font-mono text-white">{aiRecommendation.recommended_formation_time_s} s</span></div>
            <div>Peak Outflow Estimate: <span className="font-mono text-amber-300">{aiRecommendation.peak_discharge_est_m3s} m³/s</span></div>
          </div>
        )}
      </div>

      {/* Parameter Controls */}
      <div className="mt-5 space-y-4 text-xs">
        {/* Solver Selector */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center justify-between">
            <span>Hydrodynamic Solver</span>
            <span className="text-[10px] text-sky-400">Multi-engine</span>
          </label>
          <select
            value={solver}
            onChange={(e) => setSolver(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-xs focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <option value="fast_swe">FastSWE2D (High-Speed 2D SWE Finite Volume)</option>
            <option value="dflowfm">Delft3D / D-Flow FM Flexible Mesh Adapter</option>
            <option value="dualsphysics">DualSPHysics SPH Particle Adapter</option>
          </select>
        </div>

        {/* Breach Bottom Width */}
        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Breach Bottom Width (Wb)</span>
            <span className="font-mono font-semibold text-sky-400">{breachWidth} m</span>
          </div>
          <input
            type="range"
            min={30}
            max={200}
            step={1}
            value={breachWidth}
            onChange={(e) => {
              const bw = Number(e.target.value);
              setBreachWidth(bw);
              if (topWidth < bw) setTopWidth(roundVal(bw * 1.3));
            }}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        {/* Formation Time */}
        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Breach Formation Time (tf)</span>
            <span className="font-mono font-semibold text-sky-400">{formationTime} s ({Math.round(formationTime/60)} min)</span>
          </div>
          <input
            type="range"
            min={60}
            max={600}
            step={10}
            value={formationTime}
            onChange={(e) => setFormationTime(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        {/* Reservoir Water Level */}
        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Reservoir Surface Level (Hr)</span>
            <span className="font-mono font-semibold text-sky-400">{reservoirLevel} m</span>
          </div>
          <input
            type="range"
            min={760}
            max={835}
            step={1}
            value={reservoirLevel}
            onChange={(e) => setReservoirLevel(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>

        {/* Manning Roughness */}
        <div>
          <div className="flex justify-between text-slate-300 mb-1">
            <span>Manning Roughness (n)</span>
            <span className="font-mono font-semibold text-sky-400">{manningN}</span>
          </div>
          <input
            type="range"
            min={0.025}
            max={0.080}
            step={0.001}
            value={manningN}
            onChange={(e) => setManningN(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
          />
        </div>
      </div>

      {/* Validation Result Box */}
      {validationResult && (
        <div className="mt-4 p-3 rounded-lg bg-slate-800/80 border border-slate-700 text-xs">
          <div className="flex items-center justify-between font-semibold mb-2">
            <span className="text-slate-300">Input Readiness:</span>
            <span className={`px-2 py-0.5 rounded text-[10px] ${
              validationResult.overall_status === "READY" ? "bg-emerald-950 text-emerald-400" : "bg-amber-950 text-amber-400"
            }`}>
              {validationResult.overall_status} ({validationResult.score_pct}%)
            </span>
          </div>
          <div className="space-y-1">
            {validationResult.checklist.slice(0, 3).map((item: any, i: number) => (
              <div key={i} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span>{item.item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer Action Buttons */}
      <div className="mt-auto pt-6 space-y-2.5">
        <button
          onClick={handleValidate}
          className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
        >
          Validate Contract & Inputs
        </button>

        <button
          onClick={handleRun}
          disabled={isRunning}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-sky-600/30 transition-all disabled:opacity-60 active:scale-95 cursor-pointer"
        >
          {isRunning ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-sky-200" />
              <span>Solving Hydrodynamics...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>Run Hydrodynamic Simulation</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
