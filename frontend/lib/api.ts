const getApiBase = (): string => {
  const envUrl = (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) || "http://localhost:8000/api/v1";
  const trimmed = envUrl.trim().replace(/\/+$/, "");
  return trimmed.endsWith("/api/v1") ? trimmed : `${trimmed}/api/v1`;
};

export const API_BASE = getApiBase();

export interface Project {
  id: string;
  name: string;
  description: string;
}

export interface Dam {
  id: string;
  name: string;
  dam_type: string;
  crest_elevation_m: number;
  height_m: number;
  reservoir_storage_m3: number;
  location_lon: number;
  location_lat: number;
}

export interface Scenario {
  id: string;
  project_id: string;
  name: string;
  status: string;
  engine_config: any;
}

export interface Simulation {
  id: string;
  scenario_id: string;
  solver: string;
  status: string;
  progress_pct: number;
  current_phase: string;
  metrics_summary: any;
  error_message?: string;
}

export interface AffectedVillage {
  name: string;
  arrival_time_min: number;
  max_depth_m: number;
  peak_velocity_ms: number;
  population_est: number;
  risk_level: string;
  coordinates?: [number, number];
  hazard_rating?: number;
}

export interface ImpactData {
  simulation_id: string;
  peak_flood_area_km2: number;
  max_depth_m: number;
  max_velocity_ms: number;
  earliest_arrival_min: number;
  affected_villages_count: number;
  affected_villages: AffectedVillage[];
  affected_roads_km: number;
  affected_bridges_count: number;
  affected_hospitals_count: number;
  affected_schools_count: number;
  hazard_zones_km2: Record<string, number>;
}

export interface ValidationData {
  simulation_id: string;
  observed_flood_id: string;
  source: string;
  iou: number;
  csi: number;
  fpr: number;
  fnr: number;
  confusion_matrix: {
    tp_cells: number;
    fp_cells: number;
    fn_cells: number;
    tn_cells: number;
  };
  predicted_area_km2: number;
  observed_area_km2: number;
  intersection_area_km2: number;
}

export const api = {
  async checkHealth(): Promise<{ status: string; service?: string } | null> {
    try {
      const rootUrl = API_BASE.replace(/\/api\/v1$/, "");
      const res = await fetch(`${rootUrl}/api/health`);
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },

  async getProjects(): Promise<Project[]> {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      console.warn("[API] Could not fetch projects (backend may be starting or offline):", err);
      return [];
    }
  },

  async getProjectDams(projectId: string): Promise<Dam[]> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/dams`);
    return res.json();
  },

  async getProjectAssets(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/assets`);
    return res.json();
  },

  async getProjectScenarios(projectId: string): Promise<Scenario[]> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/scenarios`);
    return res.json();
  },

  async runSimulation(
    scenarioId: string,
    solver = "fast_swe",
    asyncMode = false,
    parameterOverrides?: Record<string, any>
  ): Promise<Simulation> {
    const res = await fetch(`${API_BASE}/simulations/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_id: scenarioId,
        solvers: [solver],
        async_mode: asyncMode,
        parameter_overrides: parameterOverrides,
      }),
    });
    return res.json();
  },

  async getSimulationStatus(simId: string): Promise<Simulation> {
    const res = await fetch(`${API_BASE}/simulations/${simId}/status`);
    return res.json();
  },

  async getSimulationImpact(simId: string): Promise<ImpactData> {
    const res = await fetch(`${API_BASE}/simulations/${simId}/impact`);
    return res.json();
  },

  async getSimulationValidation(simId: string): Promise<ValidationData> {
    const res = await fetch(`${API_BASE}/validation/${simId}`);
    return res.json();
  },

  async getSatelliteFlood(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/validation/satellite/observed_flood/${projectId}`);
    return res.json();
  },

  async getLatestSimulation(scenarioId?: string): Promise<Simulation | null> {
    const url = scenarioId
      ? `${API_BASE}/simulations/latest?scenario_id=${scenarioId}`
      : `${API_BASE}/simulations/latest`;
    const res = await fetch(url);
    if (!res.ok) return null;
    return res.json();
  },

  async getFloodExtentGeojson(simId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/simulations/${simId}/flood_extent.geojson`);
    if (!res.ok) return null;
    return res.json();
  },

  async getStepFloodExtent(simId: string, step: number): Promise<any> {
    const res = await fetch(`${API_BASE}/simulations/${simId}/step/${step}.geojson`);
    if (!res.ok) return null;
    return res.json();
  },

  async getTimeline(simId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/simulations/${simId}/timeline`);
    return res.json();
  },

  async recommendBreachParams(params: {
    dam_height_m: number;
    reservoir_storage_m3: number;
    dam_type?: string;
    failure_mode?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/parameter-recommendation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    return res.json();
  },

  async checkInputQuality(scenario: any): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/input-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    return res.json();
  },

  async interpretResult(simId: string, query: string): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/result-interpretation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_id: simId, query }),
    });
    return res.json();
  },

  async runSurrogate(scenario: any): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/surrogate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario }),
    });
    return res.json();
  },

  async runCalibration(simId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/ai/calibration/${simId}`, {
      method: "POST",
    });
    return res.json();
  },

  getExportUrl(simId: string, format: string): string {
    return `${API_BASE}/exports/${simId}/download?format=${format}`;
  },
};
