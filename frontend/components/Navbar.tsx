"use client";

import React from "react";
import { Waves, Sparkles, Download, Layers, ShieldAlert, Satellite, Activity } from "lucide-react";
import { Project } from "@/lib/api";

interface NavbarProps {
  projects: Project[];
  selectedProjectId: string;
  onSelectProject: (id: string) => void;
  activeTab: "scenario" | "impact" | "validation";
  onTabChange: (tab: "scenario" | "impact" | "validation") => void;
  onOpenAi: () => void;
  onOpenExport: () => void;
  isSimulating: boolean;
}

export default function Navbar({
  projects,
  selectedProjectId,
  onSelectProject,
  activeTab,
  onTabChange,
  onOpenAi,
  onOpenExport,
  isSimulating,
}: NavbarProps) {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-950/90 backdrop-blur-md px-4 flex items-center justify-between z-30 shrink-0 select-none">
      {/* Brand & Project Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-blue-500 flex items-center justify-center text-white shadow-md shadow-sky-600/30 font-bold">
            <Waves className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-extrabold text-sm text-white tracking-tight leading-none">HYDRO-AI</h1>
            <span className="text-[10px] text-slate-400 font-medium">Dam-Break Decision Support</span>
          </div>
        </div>

        {/* Project Selector Dropdown */}
        <div className="h-5 w-px bg-slate-800" />
        <select
          value={selectedProjectId}
          onChange={(e) => onSelectProject(e.target.value)}
          className="bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1 text-xs text-slate-200 font-medium focus:ring-1 focus:ring-sky-500 focus:outline-none"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Center Navigation Tabs */}
      <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium">
        <button
          onClick={() => onTabChange("scenario")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
            activeTab === "scenario"
              ? "bg-sky-600 text-white shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          Scenario & Solver
        </button>

        <button
          onClick={() => onTabChange("impact")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
            activeTab === "impact"
              ? "bg-rose-600 text-white shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          Spatial Impact
        </button>

        <button
          onClick={() => onTabChange("validation")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
            activeTab === "validation"
              ? "bg-fuchsia-600 text-white shadow-sm"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Satellite className="w-3.5 h-3.5" />
          Satellite Validation
        </button>
      </div>

      {/* Right System Indicators & Modals */}
      <div className="flex items-center gap-2.5">
        {/* Solver status pills */}
        <div className="hidden lg:flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            FastSWE2D
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-sky-400">
            D-Flow FM
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-fuchsia-400">
            Sentinel-1
          </span>
        </div>

        {/* AI Assistant Button */}
        <button
          onClick={onOpenAi}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-violet-600/90 to-indigo-600/90 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-violet-600/20 transition"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          AI Assistant
        </button>

        {/* Export Center Button */}
        <button
          onClick={onOpenExport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
        >
          <Download className="w-3.5 h-3.5 text-sky-400" />
          Export
        </button>
      </div>
    </header>
  );
}
