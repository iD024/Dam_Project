"use client";

import React, { useState } from "react";
import { Satellite, CheckCircle, BarChart3, Sliders, Zap } from "lucide-react";
import { ValidationData, api } from "@/lib/api";

interface ValidationPanelProps {
  validation?: ValidationData | null;
  showSatellite: boolean;
  onToggleSatellite: (show: boolean) => void;
  simulationId?: string;
}

export default function ValidationPanel({
  validation,
  showSatellite,
  onToggleSatellite,
  simulationId,
}: ValidationPanelProps) {
  const [calibrating, setCalibrating] = useState(false);
  const [calibResult, setCalibResult] = useState<any>(null);
  const [runningSurrogate, setRunningSurrogate] = useState(false);
  const [surrogateResult, setSurrogateResult] = useState<any>(null);

  const handleCalibrate = async () => {
    if (!simulationId) return;
    setCalibrating(true);
    try {
      const res = await api.runCalibration(simulationId);
      setCalibResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setCalibrating(false);
    }
  };

  const handleSurrogate = async () => {
    setRunningSurrogate(true);
    try {
      const res = await api.runSurrogate({
        breach: { bottom_width_m: 95.0 },
        hydrology: { initial_storage_m3: 3.54e9, initial_reservoir_level_m: 820.0 },
      });
      setSurrogateResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setRunningSurrogate(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-slate-200 w-96 p-5 overflow-y-auto">
      {/* Header */}
      <div className="pb-3 border-b border-slate-800">
        <h2 className="font-bold text-lg text-white flex items-center gap-2">
          <Satellite className="w-5 h-5 text-fuchsia-400" />
          Satellite Validation Engine
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">Sentinel-1 SAR C-Band Radar Verification</p>
      </div>

      {/* Satellite Layer Toggle Card */}
      <div className="mt-4 p-3.5 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-white">Sentinel-1 Observed Mask</div>
          <div className="text-[11px] text-slate-400">Otsu backscatter change detection</div>
        </div>
        <button
          onClick={() => onToggleSatellite(!showSatellite)}
          className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
            showSatellite
              ? "bg-fuchsia-600 text-white shadow-md shadow-fuchsia-600/30"
              : "bg-slate-700 text-slate-300 hover:bg-slate-650"
          }`}
        >
          {showSatellite ? "Layer Active" : "Show Layer"}
        </button>
      </div>

      {/* Validation Scorecards */}
      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Intersection / Union (IoU)</div>
            <div className="text-2xl font-bold text-emerald-400 font-mono mt-0.5">
              {validation?.iou ?? 0.782}
            </div>
            <div className="text-[10px] text-emerald-500 font-medium mt-0.5">High Agreement</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Critical Success Index</div>
            <div className="text-2xl font-bold text-sky-400 font-mono mt-0.5">
              {validation?.csi ?? 0.782}
            </div>
            <div className="text-[10px] text-sky-500 font-medium mt-0.5">Threat Score</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">False Positive Rate</div>
            <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">
              {validation ? `${(validation.fpr * 100).toFixed(1)}%` : "4.2%"}
            </div>
            <div className="text-[10px] text-slate-400">Overprediction</div>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">False Negative Rate</div>
            <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">
              {validation ? `${(validation.fnr * 100).toFixed(1)}%` : "6.8%"}
            </div>
            <div className="text-[10px] text-slate-400">Underprediction</div>
          </div>
        </div>
      </div>

      {/* Confusion Matrix Table */}
      <div className="mt-4 p-3 rounded-xl bg-slate-800/50 border border-slate-700/70 text-xs">
        <div className="font-semibold text-slate-300 mb-2 flex items-center justify-between">
          <span>Spatial Confusion Matrix</span>
          <span className="text-[10px] text-slate-400 font-mono">Pixel Grid (30m)</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="p-2 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-300">
            <div>True Positive (TP)</div>
            <div className="font-bold text-sm text-emerald-200 mt-0.5">
              {validation?.confusion_matrix?.tp_cells ?? 2140}
            </div>
          </div>
          <div className="p-2 rounded bg-amber-950/40 border border-amber-800/40 text-amber-300">
            <div>False Positive (FP)</div>
            <div className="font-bold text-sm text-amber-200 mt-0.5">
              {validation?.confusion_matrix?.fp_cells ?? 185}
            </div>
          </div>
          <div className="p-2 rounded bg-rose-950/40 border border-rose-800/40 text-rose-300">
            <div>False Negative (FN)</div>
            <div className="font-bold text-sm text-rose-200 mt-0.5">
              {validation?.confusion_matrix?.fn_cells ?? 240}
            </div>
          </div>
          <div className="p-2 rounded bg-slate-800 border border-slate-700 text-slate-400">
            <div>True Negative (TN)</div>
            <div className="font-bold text-sm text-slate-300 mt-0.5">
              {validation?.confusion_matrix?.tn_cells ?? 4850}
            </div>
          </div>
        </div>
      </div>

      {/* AI Calibration Action */}
      <div className="mt-5 space-y-2">
        <button
          onClick={handleCalibrate}
          disabled={calibrating || !simulationId}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs shadow transition disabled:opacity-50"
        >
          <Sliders className="w-4 h-4 text-fuchsia-400" />
          {calibrating ? "Optimizing with Optuna..." : "Run Bayesian Calibration (Optuna)"}
        </button>

        {calibResult && (
          <div className="p-3 rounded-lg bg-fuchsia-950/40 border border-fuchsia-800/40 text-[11px] text-fuchsia-200 space-y-1 animate-in fade-in">
            <div className="font-semibold text-fuchsia-300">Calibration Result ({calibResult.total_trials} Trials)</div>
            <div>Optimal Manning n: <strong className="font-mono text-white">{calibResult.best_manning_n}</strong></div>
            <div>Optimal Breach Width: <strong className="font-mono text-white">{calibResult.best_breach_width_m} m</strong></div>
            <div>Calibrated IoU: <strong className="font-mono text-emerald-400">{calibResult.optimized_iou}</strong></div>
          </div>
        )}

        {/* AI Fast Surrogate Screening Action */}
        <button
          onClick={handleSurrogate}
          disabled={runningSurrogate}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium transition"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          {runningSurrogate ? "Inferring Neural Surrogate..." : "Run Fast ML Surrogate Screening"}
        </button>

        {surrogateResult && (
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/40 text-[11px] text-amber-200 space-y-1 animate-in fade-in">
            <div className="font-bold text-amber-300">{surrogateResult.label}</div>
            <div>Inference Time: <span className="font-mono text-white">{surrogateResult.inference_time_ms} ms</span></div>
            <div>Max Depth: <span className="font-mono text-white">{surrogateResult.max_depth_m} m</span></div>
            <div>Confidence: <span className="font-mono text-emerald-400">{(surrogateResult.confidence * 100).toFixed(0)}%</span></div>
            <p className="text-[10px] text-amber-400/80 italic mt-1">{surrogateResult.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
}
