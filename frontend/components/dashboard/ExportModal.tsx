"use client";

import React from "react";
import { Download, FileText, Globe, MapPin, X, Archive } from "lucide-react";
import { api } from "@/lib/api";

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  simulationId?: string;
}

export default function ExportModal({ isOpen, onClose, simulationId }: ExportModalProps) {
  if (!isOpen) return null;

  const exportFormats = [
    {
      id: "geojson",
      name: "GeoJSON Flood Boundary",
      ext: ".geojson",
      desc: "Standard OGC vector polygon formatted for web mapping and GIS pipelines.",
      icon: Globe,
      color: "text-emerald-400 bg-emerald-950/40 border-emerald-800/40",
    },
    {
      id: "kml",
      name: "Google Earth Vector Overlay",
      ext: ".kml",
      desc: "Styled 3D polygon GroundOverlay for Google Earth 3D inspection.",
      icon: MapPin,
      color: "text-sky-400 bg-sky-950/40 border-sky-800/40",
    },
    {
      id: "shp",
      name: "ESRI Shapefile Bundle",
      ext: "_shp.zip",
      desc: "Zipped Shapefile (.shp, .shx, .dbf, .prj) with hazard classification codes.",
      icon: Archive,
      color: "text-amber-400 bg-amber-950/40 border-amber-800/40",
    },
    {
      id: "geotiff",
      name: "GeoTIFF Hydrodynamic Rasters",
      ext: "_rasters.zip",
      desc: "High-resolution rasters for Max Depth, Max Velocity, and Arrival Time.",
      icon: FileText,
      color: "text-indigo-400 bg-indigo-950/40 border-indigo-800/40",
    },
    {
      id: "csv",
      name: "Tabular Metrics & Assets",
      ext: ".csv",
      desc: "Summary metrics, peak depths, and affected settlement tables in CSV.",
      icon: FileText,
      color: "text-slate-400 bg-slate-800/60 border-slate-700/60",
    },
  ];

  const handleDownload = (format: string) => {
    if (!simulationId) return;
    const url = api.getExportUrl(simulationId, format);
    window.open(url, "_blank");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-sky-600/20 text-sky-400 border border-sky-500/30">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">GIS Export Center</h3>
              <p className="text-xs text-slate-400">Download standardized hydrodynamic assets</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Format List */}
        <div className="p-5 space-y-2.5">
          {exportFormats.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.id}
                className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 hover:border-slate-600 transition flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl border ${f.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-white flex items-center gap-1.5">
                      {f.name}
                      <span className="font-mono text-[10px] text-slate-400 font-normal">{f.ext}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">{f.desc}</p>
                  </div>
                </div>

                <button
                  onClick={() => handleDownload(f.id)}
                  disabled={!simulationId}
                  className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow transition disabled:opacity-40 shrink-0 ml-3 flex items-center gap-1"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </button>
              </div>
            );
          })}
        </div>

        <div className="px-5 py-3 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-400 text-center">
          Exports adhere to OGC geospatial specifications and CRS: EPSG:4326 / UTM 44N.
        </div>
      </div>
    </div>
  );
}
