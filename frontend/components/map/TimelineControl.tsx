"use client";

import React from "react";
import { Play, Pause, RotateCcw, ChevronLeft, ChevronRight, Gauge } from "lucide-react";

interface TimelineProps {
  currentStep: number;
  totalSteps: number;
  timeSeconds: number;
  isPlaying: boolean;
  onPlayToggle: () => void;
  onStepChange: (step: number) => void;
  onReset: () => void;
  playbackSpeed?: number;
  onSpeedChange?: (speed: number) => void;
  maxTimeSeconds?: number;
}

export default function TimelineControl({
  currentStep,
  totalSteps,
  timeSeconds,
  isPlaying,
  onPlayToggle,
  onStepChange,
  onReset,
  playbackSpeed = 1,
  onSpeedChange,
  maxTimeSeconds = 7200,
}: TimelineProps) {
  // Format seconds to HH:MM:SS
  const formatTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    return `T + ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleStepBack = () => {
    onStepChange(Math.max(0, currentStep - 1));
  };

  const handleStepForward = () => {
    onStepChange(Math.min(totalSteps - 1, currentStep + 1));
  };

  const nextSpeed = () => {
    if (!onSpeedChange) return;
    if (playbackSpeed === 1) onSpeedChange(2);
    else if (playbackSpeed === 2) onSpeedChange(4);
    else onSpeedChange(1);
  };

  return (
    <div className="bg-slate-900/95 backdrop-blur-md border border-slate-700/90 rounded-2xl px-5 py-3 shadow-2xl flex items-center gap-3.5 w-full max-w-3xl mx-auto select-none transition-all">
      {/* Reset to T=0 */}
      <button
        onClick={onReset}
        className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition active:scale-95 shrink-0"
        title="Reset flood propagation to T=0"
      >
        <RotateCcw className="w-4 h-4" />
      </button>

      {/* Step Back */}
      <button
        onClick={handleStepBack}
        disabled={currentStep <= 0}
        className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition disabled:opacity-30 disabled:hover:bg-transparent shrink-0"
        title="Previous Timestep (-5 min)"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* Play/Pause Simulation Button */}
      <button
        onClick={onPlayToggle}
        className={`flex items-center justify-center w-11 h-11 rounded-xl font-medium shadow-lg transition-all active:scale-95 shrink-0 ${
          isPlaying
            ? "bg-amber-600 hover:bg-amber-500 text-white ring-2 ring-amber-400/50 shadow-amber-600/30 animate-pulse"
            : "bg-sky-600 hover:bg-sky-500 text-white shadow-sky-600/30 hover:scale-105"
        }`}
        title={isPlaying ? "Pause Simulation Playback" : "Play Hydrodynamic Wave Propagation"}
      >
        {isPlaying ? <Pause className="w-5 h-5 fill-white" /> : <Play className="w-5 h-5 ml-0.5 fill-white" />}
      </button>

      {/* Step Forward */}
      <button
        onClick={handleStepForward}
        disabled={currentStep >= totalSteps - 1}
        className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition disabled:opacity-30 disabled:hover:bg-transparent shrink-0"
        title="Next Timestep (+5 min)"
      >
        <ChevronRight className="w-4 h-4" />
      </button>

      {/* Time Display */}
      <div className="font-mono text-xs font-bold text-sky-400 min-w-[110px] bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800 text-center">
        {formatTime(timeSeconds)}
      </div>

      {/* Range Slider with Interactive Track */}
      <div className="flex-1 relative flex items-center group">
        <input
          type="range"
          min={0}
          max={Math.max(totalSteps - 1, 1)}
          value={currentStep}
          onChange={(e) => onStepChange(Number(e.target.value))}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500 group-hover:accent-sky-400 transition"
        />
      </div>

      {/* Step Counter Badge */}
      <div className="text-[11px] text-slate-300 font-mono bg-slate-800/80 px-2 py-1 rounded-md border border-slate-700/60 shrink-0">
        Step {currentStep + 1}/{totalSteps}
      </div>

      {/* Speed Control Button */}
      {onSpeedChange && (
        <button
          onClick={nextSpeed}
          className="text-xs font-mono font-semibold px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition shrink-0 flex items-center gap-1"
          title="Toggle playback speed (1x, 2x, 4x)"
        >
          <Gauge className="w-3 h-3 text-sky-400" />
          <span>{playbackSpeed}x</span>
        </button>
      )}
    </div>
  );
}
