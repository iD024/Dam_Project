from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from backend.schemas.scenario_contract import ScenarioContract

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class DamBase(BaseModel):
    name: str
    dam_type: str = "Embankment"
    crest_elevation_m: float
    height_m: float
    crest_length_m: Optional[float] = None
    reservoir_storage_m3: float
    location_lon: float
    location_lat: float
    properties: Dict[str, Any] = Field(default_factory=dict)

class DamCreate(DamBase):
    project_id: str

class DamResponse(DamBase):
    id: str
    project_id: str
    created_at: datetime

    model_config = {"from_attributes": True}

class RiverBase(BaseModel):
    name: str
    basin_name: Optional[str] = None
    length_km: Optional[float] = None
    geom_geojson: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

class RiverCreate(RiverBase):
    project_id: str

class RiverResponse(RiverBase):
    id: str
    project_id: str
    created_at: datetime

    model_config = {"from_attributes": True}

class ScenarioCreate(BaseModel):
    project_id: str
    dam_id: Optional[str] = None
    river_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    engine_config: ScenarioContract

class ScenarioResponse(BaseModel):
    id: str
    project_id: str
    dam_id: Optional[str] = None
    river_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: str
    engine_config: Dict[str, Any]
    scenario_hash: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class SimulationRunRequest(BaseModel):
    scenario_id: str
    solvers: List[str] = Field(default_factory=lambda: ["fast_swe"])
    async_mode: bool = False
    parameter_overrides: Optional[Dict[str, Any]] = None

class SimulationResponse(BaseModel):
    id: str
    scenario_id: str
    solver: str
    solver_version: str
    status: str
    progress_pct: float
    current_phase: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class SimulationStatusResponse(BaseModel):
    id: str
    status: str
    progress_pct: float
    current_phase: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

class SimulationResultResponse(BaseModel):
    id: str
    simulation_id: str
    product_type: str
    file_path: str
    media_type: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

class AffectedVillage(BaseModel):
    name: str
    arrival_time_min: float
    max_depth_m: float
    peak_velocity_ms: float
    population_est: int = 0
    risk_level: str = "HIGH"  # LOW, MEDIUM, HIGH, CRITICAL
    coordinates: Optional[List[float]] = None
    hazard_rating: Optional[float] = None

class ImpactResponse(BaseModel):
    simulation_id: str
    peak_flood_area_km2: float
    max_depth_m: float
    max_velocity_ms: float
    earliest_arrival_min: float
    affected_villages_count: int
    affected_villages: List[AffectedVillage] = Field(default_factory=list)
    affected_roads_km: float
    affected_bridges_count: int
    affected_hospitals_count: int
    affected_schools_count: int
    hazard_zones_km2: Dict[str, float] = Field(default_factory=dict)

class ValidationResponse(BaseModel):
    simulation_id: str
    observed_flood_id: str
    source: str
    iou: float
    csi: float
    fpr: float
    fnr: float
    confusion_matrix: Dict[str, int]
    predicted_area_km2: float
    observed_area_km2: float
    intersection_area_km2: float
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)

class AIInputCheckRequest(BaseModel):
    scenario: ScenarioContract

class CheckItem(BaseModel):
    item: str
    status: str  # READY, WARNING, MISSING, INVALID
    details: str

class AIInputCheckResponse(BaseModel):
    overall_status: str  # READY, WARNING, ACTION_REQUIRED
    score_pct: float
    checklist: List[CheckItem]
    recommendations: List[str]

class AIParameterRecommendationRequest(BaseModel):
    dam_height_m: float
    reservoir_storage_m3: float
    dam_type: str = "embankment"
    failure_mode: str = "overtopping"

class AIParameterRecommendationResponse(BaseModel):
    method: str
    recommended_breach_width_m: float
    breach_width_range_m: List[float]
    recommended_formation_time_s: float
    formation_time_range_s: List[float]
    recommended_side_slope_hv: float
    peak_discharge_est_m3s: float
    manning_n_recommendations: Dict[str, float]
    confidence_score: float
    citations: List[str]

class AIResultInterpretationRequest(BaseModel):
    simulation_id: str
    query: str

class AIResultInterpretationResponse(BaseModel):
    simulation_id: str
    query: str
    answer: str
    grounding_data: Dict[str, Any]
    confidence: float
