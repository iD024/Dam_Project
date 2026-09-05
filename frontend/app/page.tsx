"use client";

import React, { useState, useEffect, useRef } from "react";
import Navbar from "@/components/Navbar";
import dynamic from "next/dynamic";
const MapLibreView = dynamic(() => import("@/components/map/MapLibreView"), { ssr: false });
import TimelineControl from "@/components/map/TimelineControl";
import LayerControlPanel from "@/components/map/LayerControlPanel";
import ScenarioDrawer from "@/components/dashboard/ScenarioDrawer";
import ImpactPanel from "@/components/dashboard/ImpactPanel";
import ValidationPanel from "@/components/dashboard/ValidationPanel";
import AIAssistantModal from "@/components/ai/AIAssistantModal";
import ExportModal from "@/components/dashboard/ExportModal";
import { api, Project, Dam, Scenario, Simulation, ImpactData, ValidationData } from "@/lib/api";
import { Activity, AlertCircle, Play } from "lucide-react";

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("proj_tehri_001");
  const [activeDam, setActiveDam] = useState<Dam | undefined>();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [currentScenario, setCurrentScenario] = useState<Scenario | null>(null);

  // Simulation state
  const [currentSimulation, setCurrentSimulation] = useState<Simulation | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simProgress, setSimProgress] = useState(0);
  const [simPhase, setSimPhase] = useState("Idle");

  // Map & GIS state
  const [activeTab, setActiveTab] = useState<"scenario" | "impact" | "validation">("scenario");
  const [activeLayer, setActiveLayer] = useState<"depth" | "velocity" | "arrival" | "none">("depth");
  const [showSatelliteObserved, setShowSatelliteObserved] = useState(false);
  const [floodExtentGeojson, setFloodExtentGeojson] = useState<any>(null);
  const [stepGeojsons, setStepGeojsons] = useState<Record<string | number, any>>({});
  const [observedSatelliteGeojson, setObservedSatelliteGeojson] = useState<any>(null);
  const [focusedLocation, setFocusedLocation] = useState<[number, number] | null>(null);

  // 4D Timeline playback state
  const [timelineSlices, setTimelineSlices] = useState<any[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [isLooping, setIsLooping] = useState<boolean>(true);
  const playTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Impact and Validation data
  const [impactData, setImpactData] = useState<ImpactData | null>(null);
  const [validationData, setValidationData] = useState<ValidationData | null>(null);

  // Modals
  const [isAiOpen, setIsAiOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);

  // 1. Initial Load: Fetch Projects & Baseline Demo Data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const projs = await api.getProjects();
        setProjects(projs);
        if (projs.length > 0) {
          const defaultProj = projs.find((p) => p.id === "proj_tehri_001") || projs[0];
          setSelectedProjectId(defaultProj.id);
          loadProjectDetails(defaultProj.id);
        }
      } catch (e) {
        console.error("Failed to connect to backend:", e);
      }
    };
    loadInitialData();
  }, []);

  // 2. Load Project details when project selection changes
  const loadProjectDetails = async (projId: string) => {
    try {
      const dams = await api.getProjectDams(projId);
      if (dams.length > 0) setActiveDam(dams[0]);

      const scens = await api.getProjectScenarios(projId);
      setScenarios(scens);
      let activeScen = null;
      if (scens.length > 0) {
        activeScen = scens[0];
        setCurrentScenario(activeScen);
      }

      // Preload satellite observed mask
      const satGeojson = await api.getSatelliteFlood(projId);
      setObservedSatelliteGeojson(satGeojson);

      // Auto-load latest completed simulation for immediate water visualization
      const latestSim = await api.getLatestSimulation(activeScen?.id);
      if (latestSim) {
        setCurrentSimulation(latestSim);

        try {
          const impact = await api.getSimulationImpact(latestSim.id);
          setImpactData(impact);
        } catch (err) {
          console.warn("Could not load impact data:", err);
        }

        try {
          const val = await api.getSimulationValidation(latestSim.id);
          setValidationData(val);
        } catch (err) {
          console.warn("Could not load validation data:", err);
        }

        try {
          const timeline = await api.getTimeline(latestSim.id);
          if (timeline && timeline.slices) {
            setTimelineSlices(timeline.slices);
            if (timeline.step_geojsons) {
              setStepGeojsons(timeline.step_geojsons);
            }
            setCurrentStep(0);
            setIsPlaying(true);
          }
        } catch (err) {
          console.warn("Could not load timeline data:", err);
        }

        try {
          const geojson = await api.getFloodExtentGeojson(latestSim.id);
          if (geojson) {
            setFloodExtentGeojson(geojson);
          }
        } catch (err) {
          console.warn("Could not load flood extent:", err);
        }
      }
    } catch (e) {
      console.error("Error loading project details:", e);
    }
  };

  const handleSelectProject = (projId: string) => {
    setSelectedProjectId(projId);
    loadProjectDetails(projId);
  };

  // 3. Run Simulation Trigger
  const handleRunSimulation = async (params: any) => {
    if (!currentScenario) return;
    setIsSimulating(true);
    setSimProgress(15);
    setSimPhase("Initializing bathymetry and computational grid");

    try {
      setSimProgress(35);
      setSimPhase("Solving 2D Shallow Water Equations (SWE Finite Volume)");
      // Execute simulation with parameter overrides from ScenarioDrawer
      const sim = await api.runSimulation(currentScenario.id, params.solver, false, params);
      setCurrentSimulation(sim);
      setSimProgress(85);
      setSimPhase("Generating 4D inundation layers and spatial impacts");

      // Fetch Impact and Validation results
      try {
        const impact = await api.getSimulationImpact(sim.id);
        setImpactData(impact);
      } catch (err) {
        console.warn("Could not load impact data:", err);
      }

      try {
        const val = await api.getSimulationValidation(sim.id);
        setValidationData(val);
      } catch (err) {
        console.warn("Could not load validation data:", err);
      }

      // Fetch Timeline and GeoJSON
      const timeline = await api.getTimeline(sim.id);
      if (timeline && timeline.slices) {
        setTimelineSlices(timeline.slices);
        if (timeline.step_geojsons) {
          setStepGeojsons(timeline.step_geojsons);
        }
        // RESET TO STEP 0 AND AUTO-START DYNAMIC FLOOD PROPAGATION!
        setCurrentStep(0);
        setIsPlaying(true);
      }

      const geojson = await api.getFloodExtentGeojson(sim.id);
      if (geojson) {
        setFloodExtentGeojson(geojson);
      }

      setSimProgress(100);
      setSimPhase("Completed");
    } catch (e) {
      console.error("Simulation run failed:", e);
      setSimPhase("Execution error");
    } finally {
      setTimeout(() => {
        setIsSimulating(false);
      }, 500);
    }
  };

  // 4. Timeline Playback loop
  useEffect(() => {
    if (isPlaying) {
      const stepInterval = Math.max(Math.round(400 / playbackSpeed), 100);
      playTimerRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          if (timelineSlices.length === 0) return 0;
          if (prev >= timelineSlices.length - 1) {
            if (isLooping) {
              return 0; // Seamless loop!
            } else {
              setIsPlaying(false);
              return prev;
            }
          }
          return prev + 1;
        });
      }, stepInterval);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, timelineSlices, playbackSpeed, isLooping]);

  const currentTimeSeconds = timelineSlices[currentStep]?.time_s || currentStep * 60;

  // Village coordinates for map pins
  const demoVillages = impactData?.affected_villages?.map((v) => {
    const coords: Record<string, [number, number]> = {
      "Koti Colony": [78.4720, 30.3650],
      "Malidewal": [78.4950, 30.3400],
      "Khand": [78.5300, 30.2950],
      "Chhiddarwala": [78.5600, 30.2400],
      "Devprayag": [78.5980, 30.1450],
    };
    return {
      name: v.name,
      coordinates: coords[v.name] || [78.53, 30.28],
      depth: v.max_depth_m,
      arrival: v.arrival_time_min,
      risk: v.risk_level,
    };
  }) || [
    { name: "Koti Colony", coordinates: [78.4720, 30.3650] as [number, number], depth: 4.2, arrival: 18.5, risk: "CRITICAL" },
    { name: "Malidewal", coordinates: [78.4950, 30.3400] as [number, number], depth: 3.5, arrival: 24.0, risk: "CRITICAL" },
    { name: "Khand", coordinates: [78.5300, 30.2950] as [number, number], depth: 2.8, arrival: 32.5, risk: "HIGH" },
    { name: "Chhiddarwala", coordinates: [78.5600, 30.2400] as [number, number], depth: 1.9, arrival: 45.0, risk: "HIGH" },
    { name: "Devprayag", coordinates: [78.5980, 30.1450] as [number, number], depth: 2.4, arrival: 62.0, risk: "HIGH" },
  ];

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navbar */}
      <Navbar
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={handleSelectProject}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onOpenAi={() => setIsAiOpen(true)}
        onOpenExport={() => setIsExportOpen(true)}
        isSimulating={isSimulating}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 relative overflow-hidden">
        {/* Left Drawer / Controls */}
        {activeTab === "scenario" && (
          <ScenarioDrawer
            dam={activeDam}
            onRunSimulation={handleRunSimulation}
            isRunning={isSimulating}
          />
        )}

        {/* Center / Full 3D Map View */}
        <div className="flex-1 relative h-full">
          <MapLibreView
            damLocation={[activeDam?.location_lon || 78.4808, activeDam?.location_lat || 30.3778]}
            damName={activeDam?.name || "Tehri Dam"}
            villages={demoVillages}
            floodExtentGeojson={floodExtentGeojson}
            stepGeojsons={stepGeojsons}
            observedSatelliteGeojson={observedSatelliteGeojson}
            activeLayer={activeLayer}
            showSatelliteObserved={showSatelliteObserved}
            timeStep={currentStep}
            maxTimeSteps={timelineSlices.length || 10}
            focusedLocation={focusedLocation}
          />

          {/* Layer Control Panel */}
          <LayerControlPanel
            activeLayer={activeLayer}
            onSelectLayer={setActiveLayer}
            showSatelliteObserved={showSatelliteObserved}
            onToggleSatellite={setShowSatelliteObserved}
          />

          {/* Simulation Progress Overlay */}
          {isSimulating && (
            <div className="absolute top-4 right-4 z-30 bg-slate-900/95 backdrop-blur-md border border-slate-700 p-4 rounded-xl shadow-2xl w-80 animate-in fade-in">
              <div className="flex items-center gap-2 text-sky-400 font-semibold text-xs mb-2">
                <Activity className="w-4 h-4 animate-spin" />
                <span>Hydrodynamic Solver Executing...</span>
              </div>
              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mb-2">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 to-blue-600 transition-all duration-300"
                  style={{ width: `${simProgress}%` }}
                />
              </div>
              <div className="text-[11px] text-slate-400 font-mono flex justify-between">
                <span>{simPhase}</span>
                <span>{simProgress}%</span>
              </div>
            </div>
          )}

          {/* Bottom Floating 4D Timeline Slider */}
          <div className="absolute bottom-6 left-0 right-0 z-20 px-6 pointer-events-none flex justify-center">
            <div className="pointer-events-auto w-full max-w-3xl">
              <TimelineControl
                currentStep={currentStep}
                totalSteps={timelineSlices.length || 10}
                timeSeconds={currentTimeSeconds}
                isPlaying={isPlaying}
                onPlayToggle={() => {
                  if (currentStep >= (timelineSlices.length - 1)) {
                    setCurrentStep(0);
                    setIsPlaying(true);
                  } else {
                    setIsPlaying(!isPlaying);
                  }
                }}
                onStepChange={setCurrentStep}
                onReset={() => {
                  setIsPlaying(false);
                  setCurrentStep(0);
                }}
                playbackSpeed={playbackSpeed}
                onSpeedChange={setPlaybackSpeed}
                isLooping={isLooping}
                onLoopToggle={() => setIsLooping(!isLooping)}
              />
            </div>
          </div>
        </div>

        {/* Right Drawer: Impact Analysis Panel */}
        {activeTab === "impact" && (
          <ImpactPanel
            impact={impactData}
            onFocusVillage={(coords) => setFocusedLocation(coords)}
          />
        )}

        {/* Right Drawer: Satellite Validation Panel */}
        {activeTab === "validation" && (
          <ValidationPanel
            validation={validationData}
            showSatellite={showSatelliteObserved}
            onToggleSatellite={setShowSatelliteObserved}
            simulationId={currentSimulation?.id || "sim_tehri_demo"}
          />
        )}
      </div>

      {/* AI Grounded Assistant Modal */}
      <AIAssistantModal
        isOpen={isAiOpen}
        onClose={() => setIsAiOpen(false)}
        simulationId={currentSimulation?.id || "sim_tehri_demo"}
      />

      {/* GIS Export Center Modal */}
      <ExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        simulationId={currentSimulation?.id || "sim_tehri_demo"}
      />
    </div>
  );
}
