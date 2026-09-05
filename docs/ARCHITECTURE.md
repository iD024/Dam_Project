# System Architecture: Dam-Break Flood Simulation & AI Decision-Support Platform

## 1. Overview
The **Dam-Break Flood Simulation & Decision-Support Platform** is a GIS-native, physics-grounded hydroinformatics application designed to model dam breaches, flash floods, and water release scenarios on any river system. It orchestrates numerical hydrodynamic solvers (D-Flow FM / Delft3D Flexible Mesh and DualSPHysics SPH), standardizes simulation outputs into scientific GIS products, performs spatial impact analysis against human settlements and infrastructure, validates predictions against satellite-observed flood masks (Sentinel-1 SAR via Google Earth Engine), and provides AI-driven assistance around the physics.

---

## 2. Logical Architecture & Data Flow

```text
                                  +-----------------------+
                                  |     USER / OPERATOR   |
                                  +-----------+-----------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------+
|                                    WEB EXPERIENCE                                       |
| Next.js / React / TypeScript / MapLibre GL / deck.gl / Tailwind CSS                    |
| - Scenario Builder: Dam/River/Breach config & AI parameter assistant                   |
| - Simulation Monitor: Real-time job status, stage logs, & progress                     |
| - GIS Map & Timeline: 4D flood depth/velocity/arrival animation, layer toggles         |
| - Comparison & Validation: Delft3D vs SPH, Simulated vs Sentinel-1 Observed            |
| - Decision Support & Export: Affected villages, roads, hospitals, SHP/KML/GeoTIFF       |
+---------------------------------------------+-------------------------------------------+
                                              | HTTPS / REST / SSE
                                              v
+-----------------------------------------------------------------------------------------+
|                               FASTAPI BACKEND & ORCHESTRATION                          |
| - API Endpoints: /projects, /dams, /rivers, /scenarios, /simulations, /validation, /ai   |
| - Scenario Validator & Canonical Data Contract verification                            |
| - Background Job Dispatcher & Progress Tracking                                        |
| - AI Services: Input Quality Checker, Parameter Recommender, Result Interpreter RAG   |
+---------------------+-----------------------+-----------------------+-------------------+
                      |                       |                       |
                      v                       v                       v
              +---------------+       +---------------+       +---------------+
              |  PostgreSQL   |       | Redis Broker  |       | MinIO / S3    |
              |   + PostGIS   |       | & Pub/Sub     |       | Object Store  |
              | (Metadata,    |       | (Task queue & |       | (DEM COGs,    |
              | Vectors,      |       | live progress |       | NetCDF, TIFs, |
              | Spatial Ops)  |       | events)       |       | VTK, Exports) |
              +---------------+       +-------+-------+       +---------------+
                                              |
                                              v
                               +------------------------------+
                               |     CELERY WORKER ENGINE     |
                               +--+------------+-----------+--+
                                  |            |           |
                 +----------------+            |           +-----------------+
                 v                             v                             v
      +----------------------+      +----------------------+      +----------------------+
      |  D-Flow FM Worker    |      |  DualSPHysics Worker |      |   GIS & EO Worker    |
      | - Mesh & Bathymetry  |      | - STL generation     |      | - Copernicus DEM     |
      | - .mdu/.ext/.bc      |      | - GenCase XML setup  |      | - Sentinel-1 SAR     |
      | - 2D SWE solve       |      | - GPU/CPU execution  |      | - Change detection   |
      | - NetCDF raw output  |      | - PartVTK extraction |      | - Otsu thresholding  |
      +----------+-----------+      +----------+-----------+      +----------+-----------+
                 |                             |                             |
                 +--------------+--------------+-----------------------------+
                                |
                                v
                +------------------------------+
                | Result Normalization Engine  |
                | - NetCDF/VTK -> Raster/Mesh  |
                | - Depth, Velocity, Arrival   |
                | - Max Depth / Max Velocity   |
                | - Inundation Extent GeoJSON  |
                +---------------+--------------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
      +----------------------+      +----------------------+
      | PostGIS Spatial      |      | AI & Calibration     |
      | Impact Analysis      |      | - Optuna Calibration |
      | - Affected Villages  |      | - ML Surrogate       |
      | - Flooded Road (km)  |      | - Validation Metrics |
      | - Infrastructure     |      |   (IoU, CSI, FPR)    |
      +----------+-----------+      +----------+-----------+
                 \                             /
                  +-------------+-------------+
                                |
                                v
                    Standardized Web GIS Layers
```

---

## 3. Core Architectural Invariants

1. **Physics-First Principle**:
   The hydrodynamic solver (D-Flow FM / DualSPHysics) is the primary source of truth for physical predictions. AI never synthesizes fake physics outputs; it operates around the physics (input validation, parameter estimation, satellite calibration, fast surrogate screening, and grounded natural-language summarization).
2. **Solver Orchestration, Not Reimposition**:
   The platform automates model input preprocessing, configuration generation, worker execution, monitoring, and output normalization. It wraps standard solvers rather than rewriting a numerical hydrodynamic engine.
3. **Standardized Normalization Layer**:
   The frontend and GIS services never interact directly with solver-specific raw formats (.mdu, .dia, map.nc, .bi4, .vtk). All outputs are normalized into:
   - Time-series raster stacks (`depth/t_0000.tif`, `velocity/t_0000.tif`)
   - Maximum hazard rasters (`max_depth.tif`, `max_velocity.tif`, `arrival_time.tif`, `duration.tif`)
   - Vector polygons (`flood_extent.geojson`, hazard zones `gt_0_5m`, `gt_1_5m`, `gt_3_0m`)
   - Summary metadata (`summary.json`)
4. **Decoupled Asynchronous Execution**:
   Simulations take minutes to hours. The web server immediately returns `202 Accepted` with a `simulation_id` and dispatches Celery workers over Redis. Progress is streamed via Server-Sent Events / WebSockets or polled via REST.
5. **Separation of Physics Prediction vs. Earth Observation**:
   Simulation is predictive; satellite observation (Sentinel-1 SAR / GEE) is empirical evidence. The two meet at the **Validation Engine**, which computes objective metrics (IoU, CSI, FPR, FNR, confusion matrix).

---

## 4. Canonical Domain Contract (JSON Schema)

```json
{
  "schema_version": "1.0.0",
  "project_id": "proj_01J...",
  "dam_id": "dam_01J...",
  "river_id": "riv_01J...",
  "domain": {
    "bbox": [78.0, 29.9, 78.4, 30.3],
    "crs": "EPSG:32644"
  },
  "terrain": {
    "dem_uri": "s3://flood/input/dem/tehri_dem_10m.tif",
    "resolution_m": 10.0,
    "vertical_datum": "EGM2008",
    "conditioning": {
      "burn_river": true,
      "fill_sinks": false,
      "preserve_structures": true
    }
  },
  "hydrology": {
    "initial_reservoir_level_m": 820.0,
    "initial_storage_m3": 2400000000.0,
    "upstream_q_m3s": 1500.0,
    "downstream_bc": {
      "type": "discharge_timeseries",
      "uri": "s3://flood/input/hydro/downstream_bc.csv"
    }
  },
  "roughness": {
    "source": "landcover",
    "raster_uri": "s3://flood/input/roughness/manning_n.tif",
    "default_manning_n": 0.04
  },
  "breach": {
    "type": "trapezoidal_progressive",
    "failure_mode": "overtopping",
    "start_s": 60.0,
    "formation_time_s": 180.0,
    "bottom_width_m": 80.0,
    "top_width_m": 110.0,
    "side_slope_hv": 1.0,
    "bottom_elevation_m": 760.0,
    "hydrograph_model": "weir_dynamic"
  },
  "solvers": ["dflowfm"],
  "numerics": {
    "simulation_duration_s": 21600,
    "output_interval_s": 60,
    "max_courant": 0.9,
    "dry_threshold_m": 0.01
  },
  "products": {
    "depth": true,
    "velocity": true,
    "arrival_time": true,
    "duration": true,
    "extent_threshold_m": 0.1
  }
}
```

---

## 5. Simulation Engine Abstraction

```python
class SimulationEngine(ABC):
    @abstractmethod
    def validate(self, scenario: ScenarioContract) -> ValidationResult: ...
    @abstractmethod
    def prepare(self, scenario: ScenarioContract, workdir: Path) -> Path: ...
    @abstractmethod
    def run(self, workdir: Path, progress_callback: Callable[[float, str], None]) -> ExecutionSummary: ...
    @abstractmethod
    def parse_results(self, workdir: Path) -> RawSolverOutput: ...
    @abstractmethod
    def normalize_results(self, raw_output: RawSolverOutput, out_dir: Path) -> ResultManifest: ...
```

Implementations:
- `DFlowFMEngine`: Generates `.mdu`, boundary `.ext` and `.bc`, grid `.nc`, runs solver executable, extracts NetCDF output variables.
- `DualSPHysicsEngine`: Generates STL from DEM, writes `GenCase` XML, runs `DualSPHysics` GPU/CPU, executes `PartVTK` and `IsoSurface`.
- `FastSWE2DEngine`: Python/NumPy-based vectorized Shallow Water Equation finite-volume reference solver for rapid testing, demonstrations, and test environments where external Fortran/C++ compiled binaries are not preinstalled.

---

## 6. Database Schema (PostgreSQL + PostGIS)

Key entities:
- `projects`: ID, name, description, owner, timestamps.
- `dams`: ID, project_id, name, crest elevation, height, storage, point/polygon geometry.
- `rivers`: ID, project_id, name, centerline LineString geometry, river properties.
- `datasets`: ID, project_id, type, provider, source/object URI, checksum, CRS, bbox polygon.
- `scenarios`: ID, project_id, dam_id, name, status, engine_config (JSONB), scenario_hash, domain polygon.
- `simulations`: ID, scenario_id, solver, status, celery_task_id, progress_pct, timestamps, log_uri, work_uri.
- `simulation_results`: ID, simulation_id, product_type, object_uri, media_type, bbox, stats (min/max/mean).
- `exposure_assets`: ID, project_id, asset_type (village, road, building, bridge, hospital, school), geometry, properties.
- `observed_floods`: ID, project_id, source (Sentinel-1), acquisition_time, mask MultiPolygon geometry, raster_uri.
- `validations`: ID, simulation_id, observed_flood_id, metrics (IoU, CSI, FPR, FNR, confusion matrix).
- `exports`: ID, simulation_id, format (shp, kml, geojson, geotiff), file_uri, status.

---

## 7. AI & Machine Learning Architecture

1. **AI 1 - Input Quality Assistant**: Inspects scenario configuration, checks DEM resolution/coverage, verifies bounding box validity, flags missing boundary conditions, returns readiness status (`READY`, `WARNING`, `MISSING`, `INVALID`).
2. **AI 2 - Parameter Recommendation Assistant**: Computes empirical breach geometries and formation times using Froehlich (1995, 2008) and MacDonald-Langridge-Monopolis formulas based on dam height and reservoir volume.
3. **AI 3 - Result Interpreter RAG**: Queries structured PostGIS results and simulation summary JSON to answer natural language questions (e.g. "Which villages are inundated within 45 minutes?") with ground-truth data.
4. **AI 4 - Calibration Engine**: Utilizes Optuna to tune Manning roughness $n$ and breach parameters against observed satellite flood polygons, minimizing $(1 - \text{IoU})$.
5. **AI 5 - Surrogate Model**: Fast ML / Gradient Boosted surrogate emulator for sub-second preliminary flood screening. Clearly demarcated in UI as `[AI ESTIMATE]`.
