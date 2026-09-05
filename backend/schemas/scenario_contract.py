from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class DomainConfig(BaseModel):
    bbox: List[float] = Field(description="Bounding box [min_lon, min_lat, max_lon, max_lat] or projected [xmin, ymin, xmax, ymax]")
    crs: str = Field(default="EPSG:4326", description="Coordinate reference system")

    @field_validator("bbox")
    def validate_bbox(cls, v):
        if len(v) != 4:
            raise ValueError("Bounding box must have 4 coordinates [xmin, ymin, xmax, ymax]")
        if v[0] >= v[2] or v[1] >= v[3]:
            raise ValueError(f"Invalid bounding box: min coordinates ({v[0]}, {v[1]}) must be less than max coordinates ({v[2]}, {v[3]})")
        return v

class TerrainConditioning(BaseModel):
    burn_river: bool = True
    fill_sinks: bool = False
    preserve_structures: bool = True

class TerrainConfig(BaseModel):
    dem_uri: str = Field(description="URI or relative path to DEM GeoTIFF")
    resolution_m: float = Field(default=30.0, gt=0, description="Spatial resolution in meters")
    vertical_datum: str = Field(default="EGM2008")
    conditioning: TerrainConditioning = Field(default_factory=TerrainConditioning)

class DownstreamBC(BaseModel):
    type: str = Field(default="normal_depth", description="Boundary condition type: normal_depth, discharge_timeseries, stage_timeseries, free_outflow")
    uri: Optional[str] = None
    slope: Optional[float] = 0.001

class HydrologyConfig(BaseModel):
    initial_reservoir_level_m: float = Field(gt=0, description="Initial reservoir water level above datum (m)")
    initial_storage_m3: float = Field(gt=0, description="Initial reservoir active storage volume (m³)")
    upstream_q_m3s: Optional[float] = Field(default=0.0, description="Constant or initial upstream discharge (m³/s)")
    downstream_bc: DownstreamBC = Field(default_factory=DownstreamBC)

class RoughnessConfig(BaseModel):
    source: str = Field(default="landcover", description="Roughness source: landcover, uniform, user_raster")
    raster_uri: Optional[str] = None
    default_manning_n: float = Field(default=0.040, gt=0.005, lt=0.30, description="Default Manning roughness coefficient")

class BreachConfig(BaseModel):
    type: str = Field(default="trapezoidal_progressive", description="sudden, trapezoidal_progressive, piping, overtopping")
    failure_mode: str = Field(default="overtopping", description="overtopping, piping, foundation_failure")
    start_s: float = Field(default=0.0, ge=0, description="Time of failure initiation (s)")
    formation_time_s: float = Field(default=180.0, gt=0, description="Breach formation time (s)")
    bottom_width_m: float = Field(default=80.0, gt=0, description="Final breach bottom width (m)")
    top_width_m: float = Field(default=120.0, gt=0, description="Final breach top width (m)")
    side_slope_hv: float = Field(default=1.0, ge=0, description="Breach side slope horizontal:vertical")
    bottom_elevation_m: float = Field(default=750.0, description="Breach invert/bottom elevation (m)")
    hydrograph_model: str = Field(default="weir_dynamic", description="weir_dynamic, ritter_analytical, broich")

    @field_validator("top_width_m")
    def validate_widths(cls, v, info):
        bottom_w = info.data.get("bottom_width_m")
        if bottom_w is not None and v < bottom_w:
            raise ValueError(f"top_width_m ({v}) cannot be less than bottom_width_m ({bottom_w})")
        return v

class NumericsConfig(BaseModel):
    simulation_duration_s: float = Field(default=21600, gt=0, description="Simulation duration in seconds (e.g. 6 hours = 21600s)")
    output_interval_s: float = Field(default=60, gt=0, description="Time interval between saved output rasters (s)")
    max_courant: float = Field(default=0.85, gt=0, le=1.5, description="Maximum Courant-Friedrichs-Lewy (CFL) stability number")
    dry_threshold_m: float = Field(default=0.01, gt=0, description="Minimum water depth threshold for wetting/drying (m)")

class ProductsConfig(BaseModel):
    depth: bool = True
    velocity: bool = True
    arrival_time: bool = True
    duration: bool = True
    extent_threshold_m: float = Field(default=0.10, description="Threshold depth to classify a cell as flooded (m)")

class ScenarioContract(BaseModel):
    schema_version: str = Field(default="1.0.0")
    project_id: str
    dam_id: str
    river_id: str
    scenario_name: str = "Dam Break Scenario"
    description: Optional[str] = None
    domain: DomainConfig
    terrain: TerrainConfig
    hydrology: HydrologyConfig
    roughness: RoughnessConfig
    breach: BreachConfig
    solvers: List[str] = Field(default_factory=lambda: ["fast_swe"])
    numerics: NumericsConfig = Field(default_factory=NumericsConfig)
    products: ProductsConfig = Field(default_factory=ProductsConfig)
    provenance: Dict[str, Any] = Field(default_factory=dict)
