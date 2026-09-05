# Implementation Plan: Dam-Break Flood Simulation & AI Decision-Support Platform

## Executive Summary
This document defines the actionable implementation plan for building the complete Dam-Break Flood Simulation & AI Decision-Support Platform. The implementation is organized vertically so that each phase delivers verified, runnable software that integrates into the next.

---

## Phase Breakdown & Execution Sequence

### Phase 1: Minimum Working Foundation (Core Monorepo)
- **Goal**: Establish the repository layout, backend FastAPI app, Python 3.12 environment via `uv`, frontend Next.js 15+ app, and basic service health checks.
- **Components**:
  - `backend/`: FastAPI application, CORS, logging, configuration, dependency injection.
  - `frontend/`: Next.js app router, Tailwind CSS, layout, navigation, API client.
  - `tests/`: Pytest test harness and configuration.
  - Root `package.json` / Makefile / run scripts.
- **Verification**: `pytest` passes, frontend builds and runs, backend `/api/health` returns status OK.

### Phase 2: Canonical Data Models & Database Layer
- **Goal**: Implement canonical data models in SQLAlchemy and Pydantic v2 representing Projects, Dams, Rivers, Datasets, Scenarios, Simulations, Results, Assets, and Validations.
- **Components**:
  - `backend/models/`: SQLAlchemy ORM models with PostGIS / GeoJSON geometry support.
  - `backend/schemas/`: Pydantic models for request/response validation.
  - `backend/database.py`: Database session manager supporting SQLite + SpatiaLite / PostgreSQL + PostGIS.
  - Scenario Contract Schema (`scenario.schema.json`).
- **Verification**: Unit tests validating scenario parsing, breach constraints, and DB CRUD operations.

### Phase 3: Geospatial Preprocessing & Scenario Builder
- **Goal**: Provide automated DEM processing, domain bounding, river geometry alignment, and Manning roughness calculation.
- **Components**:
  - `backend/services/preprocessing/dem.py`: Reprojection, clipping, depression checking, slope calculation.
  - `backend/services/preprocessing/roughness.py`: Land-cover to Manning's $n$ mapping.
  - `backend/services/breach.py`: Empirical breach geometry calculator (Froehlich 1995/2008, MacDonald-Langridge-Monopolis).
- **Verification**: Preprocessing test generating conditioned DEM and Manning raster for Tehri Dam study basin.

### Phase 4: Hydrodynamic Simulation Engine Orchestration
- **Goal**: Deliver the simulation engine abstraction and working hydrodynamic solvers.
- **Components**:
  - `backend/simulation_engines/base.py`: Abstract `SimulationEngine` interface.
  - `backend/simulation_engines/fast_swe/`: 2D finite-volume Shallow Water Equation solver in vectorized NumPy with mass conservation and friction.
  - `backend/simulation_engines/dflowfm/`: Adapter writing `.mdu`, `.ext`, `.bc`, grid NetCDF, and running Deltares D-Flow FM.
  - `backend/simulation_engines/sph/`: Adapter generating STL terrain, GenCase XML, and running DualSPHysics.
  - `backend/services/simulation_service.py`: Job runner, progress tracking, and state management.
- **Verification**: Execute a complete dam-break simulation producing 4D water depth and velocity fields with mass balance verification.

### Phase 5: Standardized Result Normalization
- **Goal**: Transform raw solver outputs into standardized GIS rasters, vectors, and metadata.
- **Components**:
  - `backend/services/normalization.py`: Conversion of 2D/3D depth and velocity arrays into GeoTIFF rasters per timestep (`t_0000.tif`, etc.).
  - Computation of `max_depth.tif`, `max_velocity.tif`, `arrival_time.tif`, `duration.tif`.
  - Vectorization into `flood_extent.geojson` and hazard zones (`h > 0.5m`, `h > 1.5m`, `h > 3.0m`).
  - Production of `summary.json`.
- **Verification**: Automated test verifying GeoTIFF headers, CRS projection, no-data values, and GeoJSON validity.

### Phase 6: Web GIS Dashboard & Map Experience
- **Goal**: Build high-performance GIS interface with MapLibre GL and deck.gl.
- **Components**:
  - `frontend/components/map/MapContainer.tsx`: 3D terrain basemap, camera controls.
  - `frontend/components/map/FloodAnimationLayer.tsx`: Time slider (0 to 6 hours) rendering animated flood propagation.
  - `frontend/components/map/LayerControls.tsx`: Toggles for Depth, Velocity, Arrival Time, Dam, River, Satellite, Assets.
  - `frontend/components/dashboard/ScenarioBuilder.tsx`: Parameter configuration form with real-time validation.
  - `frontend/components/dashboard/SimulationMonitor.tsx`: Progress bar, phase indicators (prepare, mesh, solver, normalize, impact).
- **Verification**: Browser verification of scenario configuration, simulation launch, live progress, and interactive map playback.

### Phase 7: PostGIS Spatial Impact Analysis
- **Goal**: Intersect flood polygons with exposure layers to determine human and infrastructure impact.
- **Components**:
  - `backend/services/impact_analysis.py`: Spatial intersection queries for affected villages, inundated road lengths (km), flooded buildings, bridges, and critical facilities.
  - Frontend Impact Summary Cards: Live display of affected population centers, roads, and infrastructure with fly-to camera interactions.
- **Verification**: Impact query returns correct counts and road kilometers against known test exposure geometries.

### Phase 8: SPH Integration & Solver Benchmark
- **Goal**: Support particle-based simulation comparison against shallow-water continuum simulation.
- **Components**:
  - DualSPHysics simulation adapter execution and VTK post-processing.
  - Dual-engine comparison view: Side-by-side or difference map (Delft3D vs SPH), IoU metric, peak discharge comparison.
- **Verification**: Comparison module calculates IoU and highlights near-field vs. far-field differences.

### Phase 9: Satellite EO Engine (Sentinel-1 via GEE)
- **Goal**: Ingest satellite radar imagery for actual observed flood detection.
- **Components**:
  - `backend/services/satellite/gee_service.py`: Sentinel-1 GRD SAR acquisition, pre-flood vs. post-flood log-ratio backscatter change detection, Otsu thresholding, morphological filter, and flood mask polygonization.
  - Fallback/Offline mode: Pre-cached real Sentinel-1 SAR observations for the reference basin.
- **Verification**: Satellite engine generates observed flood mask polygon and displays it on the web map.

### Phase 10: Validation Engine
- **Goal**: Scientifically quantify predictive accuracy of the simulation against satellite observation.
- **Components**:
  - `backend/services/validation_service.py`: Computes IoU (Jaccard), CSI (Threat Score), FPR, FNR, and confusion matrix (TP, FP, FN, TN).
  - Visual Difference Layer: Green (TP - predicted & observed), Red (FP - overprediction), Blue (FN - underprediction).
- **Verification**: Unit tests verify metric formulas; frontend renders validation scorecards and difference layer.

### Phase 11: AI Decision-Support Layer
- **Goal**: Implement the 5 AI assistants around the physics.
- **Components**:
  - `backend/services/ai/input_quality.py`: Input readiness checklist.
  - `backend/services/ai/parameter_recommender.py`: Empirical breach geometry recommendations with confidence intervals.
  - `backend/services/ai/result_interpreter.py`: Natural-language QA agent over structured database and GIS metrics.
  - `backend/services/ai/calibration.py`: Optuna Bayesian optimization of Manning roughness and breach width.
  - `backend/services/ai/surrogate.py`: Fast ML surrogate emulator with explicit `[AI ESTIMATE]` labeling.
- **Verification**: AI services tested and integrated into the scenario builder and result dashboard.

### Phase 12: GIS Export Center
- **Goal**: Multi-format geospatial package export.
- **Components**:
  - `backend/services/export_service.py`: Export to Shapefile (`.zip` containing `.shp`, `.shx`, `.dbf`, `.prj`), KML (`GroundOverlay`), GeoJSON, and GeoTIFF.
  - Download endpoints and frontend export modal.
- **Verification**: Verify exported SHP and KML open correctly in QGIS / Google Earth.

### Phase 13: End-to-End Testing & Hardening
- **Goal**: System-wide automated testing, error resilience, and security.
- **Components**:
  - Unit, integration, and end-to-end API test suites.
  - Physical sanity checks: Mass balance conservation, no negative depths, no unexpected NaN values.
- **Verification**: 100% passing test suite across all modules.

### Phase 14: Indian Demonstration Case Studies
- **Goal**: Polish complete end-to-end demonstration flow on Indian reference dams.
- **Components**:
  - **Tehri Dam (Bhagirathi River)**: Mountainous gorge dam-break scenario.
  - **Rishi Ganga Flash Flood**: High-energy steep mountain disaster scenario.
- **Verification**: Complete 22-step demonstration flow verified in browser and logged.
