"use client";

import React, { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { Globe, Map as MapIcon, Mountain, Waves, Compass, Activity } from "lucide-react";

// Configure MapLibre Web Worker to load from static public directory to prevent Turbopack Blob Worker crash
if (typeof window !== "undefined" && (maplibregl as any).config) {
  (maplibregl as any).config.WORKER_URL = "/maplibre-gl-worker.mjs";
}

interface MapProps {
  damLocation?: [number, number];
  damName?: string;
  villages?: Array<{ name: string; coordinates: [number, number]; depth?: number; arrival?: number; risk?: string }>;
  floodExtentGeojson?: any;
  stepGeojsons?: Record<string | number, any>;
  observedSatelliteGeojson?: any;
  activeLayer: "depth" | "velocity" | "arrival" | "none";
  showSatelliteObserved: boolean;
  timeStep: number;
  maxTimeSteps: number;
  focusedLocation?: [number, number] | null;
}

const BASEMAPS = {
  satellite: {
    name: "Satellite",
    icon: Mountain,
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri, Maxar, Earthstar Geographics",
    maxzoom: 19,
  },
  topo: {
    name: "Topographic",
    icon: Globe,
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attribution: "&copy; Esri &copy; OpenStreetMap contributors",
    maxzoom: 19,
  },
  osm: {
    name: "Streets",
    icon: MapIcon,
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxzoom: 19,
  },
};

// Bhagirathi River waypoints in downstream sequence from Tehri Dam to Devprayag confluence
const RIVER_WAYPOINTS: [number, number][] = [
  [78.4808, 30.3778], // Tehri Dam (Origin)
  [78.4720, 30.3650], // Koti Colony
  [78.4850, 30.3520], // Upper Gorge
  [78.4950, 30.3400], // Malidewal
  [78.5080, 30.3200], // Mid Valley Turn
  [78.5200, 30.3050], // Chamba Valley Approach
  [78.5300, 30.2950], // Khand
  [78.5480, 30.2680], // Lower Gorge
  [78.5600, 30.2400], // Chhiddarwala
  [78.5720, 30.2050], // Canyon Approach
  [78.5860, 30.1700], // Pre-Devprayag Canyon
  [78.5980, 30.1450], // Devprayag Confluence
];

export default function MapLibreView({
  damLocation = [78.4808, 30.3778],
  damName = "Tehri Dam",
  villages = [],
  floodExtentGeojson,
  stepGeojsons = {},
  observedSatelliteGeojson,
  activeLayer,
  showSatelliteObserved,
  timeStep,
  maxTimeSteps,
  focusedLocation,
}: MapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const wavefrontMarkerRef = useRef<maplibregl.Marker | null>(null);
  const [selectedBasemap, setSelectedBasemap] = useState<"satellite" | "topo" | "osm">("satellite");

  // Determine current water GeoJSON based on active timestep
  const getCurrentFloodData = () => {
    // If we have time-step geojsons for this timestep, use it directly (even if empty features at T=0)
    if (stepGeojsons) {
      if (stepGeojsons[timeStep] !== undefined) {
        return stepGeojsons[timeStep];
      }
      if (stepGeojsons[String(timeStep)] !== undefined) {
        return stepGeojsons[String(timeStep)];
      }
    }
    // Otherwise fallback to composite flood extent if no step data exists
    if (floodExtentGeojson && floodExtentGeojson.features?.length > 0) {
      return floodExtentGeojson;
    }
    return { type: "FeatureCollection", features: [] };
  };

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize MapLibre GL Map with zero-key ESRI World Satellite Imagery & persistent raster layers
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          "satellite-tiles": {
            type: "raster",
            tiles: [BASEMAPS.satellite.url],
            tileSize: 256,
            attribution: BASEMAPS.satellite.attribution,
          },
          "topo-tiles": {
            type: "raster",
            tiles: [BASEMAPS.topo.url],
            tileSize: 256,
            attribution: BASEMAPS.topo.attribution,
          },
          "osm-tiles": {
            type: "raster",
            tiles: [BASEMAPS.osm.url],
            tileSize: 256,
            attribution: BASEMAPS.osm.attribution,
          },
        },
        layers: [
          {
            id: "basemap-satellite",
            type: "raster",
            source: "satellite-tiles",
            layout: { visibility: "visible" },
            minzoom: 0,
            maxzoom: 19,
          },
          {
            id: "basemap-topo",
            type: "raster",
            source: "topo-tiles",
            layout: { visibility: "none" },
            minzoom: 0,
            maxzoom: 19,
          },
          {
            id: "basemap-osm",
            type: "raster",
            source: "osm-tiles",
            layout: { visibility: "none" },
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [78.495, 30.345], // Centered on Bhagirathi valley path
      zoom: 12.0,
      pitch: 48,
      bearing: -12,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

    map.on("load", () => {
      // 1. River Corridor & Dynamic Hydrodynamic Streamline
      map.addSource("river-corridor", {
        type: "geojson",
        data: {
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: RIVER_WAYPOINTS,
          },
          properties: { name: "Bhagirathi River Corridor" },
        },
      });

      // River Glow underlayer (Ambient water luminescence)
      map.addLayer({
        id: "river-glow",
        type: "line",
        source: "river-corridor",
        paint: {
          "line-color": "#0ea5e9",
          "line-width": 9.0,
          "line-opacity": 0.45,
          "line-blur": 3.0,
        },
      });

      // River Centerline
      map.addLayer({
        id: "river-line",
        type: "line",
        source: "river-corridor",
        paint: {
          "line-color": "#bae6fd",
          "line-width": 3.2,
          "line-opacity": 0.9,
          "line-dasharray": [4, 1.5],
        },
      });

      // 2. Dynamic Flood Inundation Extent Source & Living Water Layer
      const initialFloodData = getCurrentFloodData();
      map.addSource("flood-extent", {
        type: "geojson",
        data: initialFloodData,
      });

      // Layer: Fluid Water Depth / Inundation Fill
      map.addLayer({
        id: "flood-depth-fill",
        type: "fill",
        source: "flood-extent",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "max_depth_m"],
            0.1, "#38bdf8",
            1.5, "#0284c7",
            3.0, "#1d4ed8",
            6.0, "#0f172a",
          ],
          "fill-opacity": 0.82,
        },
      });

      // Layer: Glowing Dynamic Shoreline Wave Stroke
      map.addLayer({
        id: "flood-depth-stroke",
        type: "line",
        source: "flood-extent",
        paint: {
          "line-color": "#7dd3fc",
          "line-width": 3.2,
          "line-opacity": 0.95,
        },
      });

      // 3. Add Observed Satellite Flood Source & Layer
      map.addSource("observed-satellite", {
        type: "geojson",
        data: observedSatelliteGeojson || { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "observed-satellite-fill",
        type: "fill",
        source: "observed-satellite",
        layout: { visibility: showSatelliteObserved ? "visible" : "none" },
        paint: {
          "fill-color": "#c026d3",
          "fill-opacity": 0.4,
        },
      });

      map.addLayer({
        id: "observed-satellite-stroke",
        type: "line",
        source: "observed-satellite",
        layout: { visibility: showSatelliteObserved ? "visible" : "none" },
        paint: {
          "line-color": "#f0abfc",
          "line-width": 2.5,
          "line-dasharray": [2, 2],
        },
      });
    });

    mapRef.current = map;
    return () => {
      if (wavefrontMarkerRef.current) {
        wavefrontMarkerRef.current.remove();
        wavefrontMarkerRef.current = null;
      }
      map.remove();
    };
  }, []);

  // Continuous living water surface animation (fluid shimmer and shoreline surge)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    let animId: number;
    let phase = 0;

    const animateWaterFluid = () => {
      phase += 0.04;
      try {
        if (map.getLayer("flood-depth-fill")) {
          // Living undulating water opacity creates dynamic fluid wave motion
          const dynamicOpacity = 0.78 + Math.sin(phase) * 0.08;
          map.setPaintProperty("flood-depth-fill", "fill-opacity", dynamicOpacity);
        }
        if (map.getLayer("flood-depth-stroke")) {
          // Shoreline surge pulse wave
          const strokeWidth = 2.6 + Math.cos(phase * 1.3) * 0.8;
          map.setPaintProperty("flood-depth-stroke", "line-width", strokeWidth);
        }
        if (map.getLayer("river-glow")) {
          // River flow surge luminescence
          const glowOpacity = 0.4 + Math.sin(phase * 1.8) * 0.15;
          map.setPaintProperty("river-glow", "line-opacity", glowOpacity);
        }
      } catch (e) {
        // Ignored if map style is reloading
      }
      animId = requestAnimationFrame(animateWaterFluid);
    };

    animId = requestAnimationFrame(animateWaterFluid);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Update Basemap Visibility cleanly without tearing down style or worker
  const handleSwitchBasemap = (type: "satellite" | "topo" | "osm") => {
    setSelectedBasemap(type);
    const map = mapRef.current;
    if (!map) return;

    map.setLayoutProperty("basemap-satellite", "visibility", type === "satellite" ? "visible" : "none");
    map.setLayoutProperty("basemap-topo", "visibility", type === "topo" ? "visible" : "none");
    map.setLayoutProperty("basemap-osm", "visibility", type === "osm" ? "visible" : "none");
  };

  // Update Dam & Village Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Dam breach origin marker
    const damEl = document.createElement("div");
    damEl.className =
      "flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-tr from-red-700 to-rose-500 text-white shadow-2xl border-2 border-white font-bold text-sm cursor-pointer hover:scale-125 transition-transform animate-pulse";
    damEl.innerHTML = "▲";
    damEl.title = `${damName} (Breach Origin)`;

    const damMarker = new maplibregl.Marker({ element: damEl })
      .setLngLat(damLocation)
      .setPopup(
        new maplibregl.Popup({ offset: 25 }).setHTML(`
          <div class="p-2.5 text-slate-800 text-xs font-sans">
            <div class="font-bold text-sm text-red-600 mb-1">${damName}</div>
            <div><strong>Crest Elevation:</strong> 839.5 m</div>
            <div><strong>Structure Height:</strong> 260.5 m</div>
            <div><strong>Active Storage:</strong> 3.54 Billion m³</div>
            <div class="mt-1.5 text-red-700 font-semibold flex items-center gap-1">
              <span>⚠</span> Breach Hydrodynamic Origin
            </div>
          </div>
        `)
      )
      .addTo(map);
    markersRef.current.push(damMarker);

    // Village markers
    villages.forEach((v) => {
      const el = document.createElement("div");
      const isCritical = v.risk === "CRITICAL";
      el.className = `flex items-center justify-center w-7 h-7 rounded-full shadow-lg border-2 border-white text-xs font-bold text-white cursor-pointer hover:scale-125 transition-transform ${
        isCritical ? "bg-rose-600" : v.risk === "HIGH" ? "bg-amber-600" : "bg-emerald-600"
      }`;
      el.innerHTML = "●";

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(v.coordinates)
        .setPopup(
          new maplibregl.Popup({ offset: 20 }).setHTML(`
            <div class="p-2.5 text-slate-800 text-xs font-sans">
              <div class="font-bold text-sm text-slate-900 mb-1">${v.name}</div>
              <div><strong>Wave Arrival:</strong> ${v.arrival ? `${v.arrival} min` : "N/A"}</div>
              <div><strong>Peak Inundation:</strong> ${v.depth ? `${v.depth} m` : "N/A"}</div>
              <div class="mt-1.5 font-semibold ${isCritical ? "text-rose-600" : "text-amber-600"}">
                Hazard Level: ${v.risk || "MONITORED"}
              </div>
            </div>
          `)
        )
        .addTo(map);
      markersRef.current.push(marker);
    });
  }, [damLocation, damName, villages]);

  // Update Dynamic Leading Wavefront Surge Marker along river corridor
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Calculate current wave crest coordinates along the river
    const fraction = Math.min(Math.max(timeStep / Math.max(maxTimeSteps - 1, 1), 0), 1);
    const floatIdx = fraction * (RIVER_WAYPOINTS.length - 1);
    const idx0 = Math.floor(floatIdx);
    const idx1 = Math.min(idx0 + 1, RIVER_WAYPOINTS.length - 1);
    const rem = floatIdx - idx0;

    const p0 = RIVER_WAYPOINTS[idx0];
    const p1 = RIVER_WAYPOINTS[idx1];
    const currentLng = p0[0] + (p1[0] - p0[0]) * rem;
    const currentLat = p0[1] + (p1[1] - p0[1]) * rem;

    const elapsedMin = Math.round(fraction * 60);
    const distKm = ((fraction) * 42.5).toFixed(1);
    const estSpeed = Math.max(12.8 - fraction * 4.2, 3.8).toFixed(1);

    if (!wavefrontMarkerRef.current) {
      const waveEl = document.createElement("div");
      waveEl.className = "relative flex items-center justify-center cursor-pointer pointer-events-auto z-40 whitespace-nowrap group";
      waveEl.innerHTML = `
        <div class="absolute w-10 h-10 rounded-full bg-cyan-400/40 animate-ping pointer-events-none"></div>
        <div class="absolute w-6 h-6 rounded-full bg-sky-500/60 animate-pulse pointer-events-none"></div>
        <div class="relative px-2.5 py-1 rounded-full bg-slate-950/95 border-2 border-cyan-400 text-cyan-300 font-mono text-[11px] font-bold shadow-2xl flex items-center gap-1.5 backdrop-blur-md transform hover:scale-110 transition-transform">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>🌊 Wave Crest T+${elapsedMin}m</span>
        </div>
      `;
      const marker = new maplibregl.Marker({ element: waveEl })
        .setLngLat([currentLng, currentLat])
        .setPopup(
          new maplibregl.Popup({ offset: 22 }).setHTML(`
            <div class="p-2 text-slate-800 text-xs font-sans">
              <div class="font-bold text-sky-700 flex items-center gap-1 mb-1">
                <span>🌊 Hydrodynamic Wave Crest</span>
              </div>
              <div><strong>Time:</strong> T + ${elapsedMin} min</div>
              <div><strong>Distance from Breach:</strong> ~${distKm} km</div>
              <div><strong>Estimated Surge Speed:</strong> ~${estSpeed} m/s</div>
            </div>
          `)
        )
        .addTo(map);
      wavefrontMarkerRef.current = marker;
    } else {
      wavefrontMarkerRef.current.setLngLat([currentLng, currentLat]);
      wavefrontMarkerRef.current.getPopup()?.setHTML(`
        <div class="p-2 text-slate-800 text-xs font-sans">
          <div class="font-bold text-sky-700 flex items-center gap-1 mb-1">
            <span>🌊 Hydrodynamic Wave Crest</span>
          </div>
          <div><strong>Time:</strong> T + ${elapsedMin} min</div>
          <div><strong>Distance from Breach:</strong> ~${distKm} km</div>
          <div><strong>Estimated Surge Speed:</strong> ~${estSpeed} m/s</div>
        </div>
      `);
    }
  }, [timeStep, maxTimeSteps]);

  // Update Flood Water Layer based on Active Timestep & GeoJSON
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const dataToSet = getCurrentFloodData();

    const applyData = () => {
      const source = map.getSource("flood-extent") as maplibregl.GeoJSONSource;
      if (source && dataToSet) {
        source.setData(dataToSet);
      }
    };

    if (map.getSource("flood-extent")) {
      applyData();
    } else {
      map.once("load", applyData);
    }
  }, [floodExtentGeojson, stepGeojsons, timeStep]);

  // Update Satellite Observed Layer
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyObserved = () => {
      const source = map.getSource("observed-satellite") as maplibregl.GeoJSONSource;
      if (source && observedSatelliteGeojson) {
        source.setData(observedSatelliteGeojson);
      }
      if (map.getLayer("observed-satellite-fill")) {
        map.setLayoutProperty(
          "observed-satellite-fill",
          "visibility",
          showSatelliteObserved ? "visible" : "none"
        );
      }
      if (map.getLayer("observed-satellite-stroke")) {
        map.setLayoutProperty(
          "observed-satellite-stroke",
          "visibility",
          showSatelliteObserved ? "visible" : "none"
        );
      }
    };

    if (map.getSource("observed-satellite")) {
      applyObserved();
    } else {
      map.once("load", applyObserved);
    }
  }, [observedSatelliteGeojson, showSatelliteObserved]);

  // Update Dynamic Color Ramp based on Active Layer (Depth vs Velocity vs Arrival)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("flood-depth-fill")) return;

    if (activeLayer === "none") {
      map.setLayoutProperty("flood-depth-fill", "visibility", "none");
      map.setLayoutProperty("flood-depth-stroke", "visibility", "none");
      return;
    }

    map.setLayoutProperty("flood-depth-fill", "visibility", "visible");
    map.setLayoutProperty("flood-depth-stroke", "visibility", "visible");

    if (activeLayer === "velocity") {
      map.setPaintProperty("flood-depth-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "max_depth_m"],
        0.1, "#fef08a",
        1.5, "#f97316",
        3.0, "#dc2626",
        6.0, "#7f1d1d",
      ]);
      map.setPaintProperty("flood-depth-stroke", "line-color", "#f97316");
    } else if (activeLayer === "arrival") {
      map.setPaintProperty("flood-depth-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "max_depth_m"],
        0.1, "#86efac",
        1.5, "#eab308",
        3.0, "#f97316",
        6.0, "#ef4444",
      ]);
      map.setPaintProperty("flood-depth-stroke", "line-color", "#22c55e");
    } else {
      // Default Water Depth Ramp (Sleek deep ocean blue to aqua)
      map.setPaintProperty("flood-depth-fill", "fill-color", [
        "interpolate",
        ["linear"],
        ["get", "max_depth_m"],
        0.1, "#38bdf8",
        1.5, "#0284c7",
        3.0, "#1d4ed8",
        6.0, "#0f172a",
      ]);
      map.setPaintProperty("flood-depth-stroke", "line-color", "#7dd3fc");
    }
  }, [activeLayer]);

  // Fly to focused location
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !focusedLocation) return;
    map.flyTo({
      center: focusedLocation,
      zoom: 13.5,
      pitch: 55,
      duration: 1800,
    });
  }, [focusedLocation]);

  const progressFraction = Math.min(Math.max(timeStep / Math.max(maxTimeSteps - 1, 1), 0), 1);
  const currentDistanceKm = (progressFraction * 42.5).toFixed(1);
  const currentElapsedMin = Math.round(progressFraction * 60);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Dynamic Hydrodynamic Wavefront Status HUD */}
      <div className="absolute top-4 left-[260px] z-20 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl px-3.5 py-2 shadow-2xl flex items-center gap-3 pointer-events-none">
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-sky-500"></span>
          </span>
          <div>
            <div className="text-[11px] font-bold text-white flex items-center gap-1.5 leading-none">
              <span>Bhagirathi Gorge Surge</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sky-950 text-sky-400 border border-sky-800/50">
                T + {currentElapsedMin}m
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
              Wavefront: <span className="text-cyan-300 font-semibold">{currentDistanceKm} km</span> downstream | Step {timeStep + 1}/{maxTimeSteps}
            </div>
          </div>
        </div>
      </div>

      {/* Floating Basemap Selector Widget (0 API Keys required) */}
      <div className="absolute top-4 right-14 z-20 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl p-1 shadow-2xl flex items-center gap-1">
        {(Object.keys(BASEMAPS) as Array<keyof typeof BASEMAPS>).map((key) => {
          const config = BASEMAPS[key];
          const Icon = config.icon;
          const isSelected = selectedBasemap === key;
          return (
            <button
              key={key}
              onClick={() => handleSwitchBasemap(key)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                isSelected
                  ? "bg-sky-600 text-white shadow-sm font-semibold"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
              title={`Switch to ${config.name} basemap`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{config.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
