# Architecture Decisions Log (ADR)

## ADR-001: Separation of Physics Solver from Web Application
- **Status**: Accepted
- **Context**: The platform requires hydrodynamic simulation (D-Flow FM and DualSPHysics). Reimplementing full numerical Navier-Stokes/Shallow Water solvers inside a web framework would be error-prone and non-viable.
- **Decision**: Orchestrate external solvers via an abstract `SimulationEngine` interface. The application prepares inputs, generates configuration files (`.mdu`, `.ext`, `.bc`, `GenCase` XML), launches solver processes in background workers, monitors progress, parses outputs, and normalizes them into standardized GIS products.
- **Consequences**: Solvers run in isolated environments. The web application remains decoupled from solver binary upgrades.

## ADR-002: Fast In-Memory Reference Solver (FastSWE2DEngine)
- **Status**: Accepted
- **Context**: D-Flow FM and DualSPHysics require specific system libraries, Fortran compilers, or NVIDIA CUDA GPUs, which may not be present in every development or CI/CD environment.
- **Decision**: In addition to `DFlowFMEngine` and `DualSPHysicsEngine`, implement `FastSWE2DEngine` — a 2D depth-averaged finite-volume Shallow Water Equations solver in vectorized Python (NumPy).
- **Consequences**: Guarantees that the entire pipeline (DEM -> Breach -> Hydrodynamics -> Depth/Velocity Rasters -> PostGIS Impact -> MapLibre Animation) can be executed, tested, and demonstrated out of the box in 100% of environments without external proprietary binaries.

## ADR-003: Standardized GIS Result Normalization
- **Status**: Accepted
- **Context**: D-Flow FM outputs unformatted UGRID NetCDF files; DualSPHysics outputs `.bi4` binary particle files or VTK meshes. Exposing these raw formats directly to frontend clients would cause excessive network latency and require complex client-side parsers.
- **Decision**: All solvers must be normalized by the worker into:
  1. Continuous GeoTIFFs (`depth/t_XXXX.tif`, `velocity/t_XXXX.tif`, `max_depth.tif`, `max_velocity.tif`, `arrival_time.tif`).
  2. Standard GeoJSON extent polygons (`flood_extent.geojson`) and hazard levels (`gt_0_5m`, `gt_1_5m`, `gt_3_0m`).
  3. Structured metadata (`summary.json`).
- **Consequences**: The frontend consumes standard COG / GeoJSON layers via MapLibre GL and deck.gl without knowing which solver generated the data.

## ADR-004: Python Environment Managed via `uv`
- **Status**: Accepted
- **Context**: The host machine has Python 3.14 system-wide, where several scientific C-extension wheels (GDAL, rasterio, scipy, torch) do not yet have stable precompiled binary wheels.
- **Decision**: Use `uv` to manage a isolated Python 3.12 virtual environment (`.venv`).
- **Consequences**: Fast dependency resolution, access to mature manylinux wheels for NumPy, SciPy, Rasterio, Shapely, GeoPandas, FastAPI, and PyTorch.

## ADR-005: GIS Client Stack: MapLibre GL + deck.gl
- **Status**: Accepted
- **Context**: Visualizing 4D flood propagation with time sliders, vector infrastructure, and 3D terrain requires high-performance WebGL rendering.
- **Decision**: Use MapLibre GL for 3D terrain, basemaps, and vector labels, combined with deck.gl (`MapboxOverlay`, `BitmapLayer`, `GeoJsonLayer`, `PathLayer`) for heavy raster and particle animations.
- **Consequences**: Smooth 60 FPS playback of flood fronts over realistic terrain.

## ADR-006: AI Around the Physics, Never In Place Of Physics
- **Status**: Accepted
- **Context**: Hackathon teams often make the mistake of replacing hydraulic simulations with LLM hallucinations or unconstrained regression models.
- **Decision**: Hydrodynamics is strictly governed by physical conservation of mass and momentum. AI is confined to:
  1. Input verification (Input Quality Assistant).
  2. Empirical parameter estimation (Froehlich/MacDonald breach equations).
  3. Satellite calibration (Optuna Bayesian optimizer tuning Manning's $n$ against Sentinel-1 flood masks).
  4. Surrogate model (clearly tagged `[AI ESTIMATE]`, trained strictly on physical solver runs).
  5. Result interpretation (RAG agent executing deterministic SQL/GIS queries).
- **Consequences**: Scientific integrity, transparency, and defensible results.

## ADR-007: Demonstration Case Studies (Tehri Dam & Rishi Ganga)
- **Status**: Accepted
- **Context**: The platform must demonstrate real-world applicability on Indian river basins.
- **Decision**: Ship pre-configured reference projects:
  1. **Tehri Dam (Uttarakhand)**: High earth-and-rockfill dam (260.5m) on the Bhagirathi River; demonstrates reservoir storage breach, steep gorge routing into Devprayag, and impact on downstream settlements.
  2. **Rishi Ganga / Chamoli Flash Flood**: Steep mountain debris/water surge showing rapid arrival times and satellite SAR detection comparison.
- **Consequences**: Enables immediate end-to-end user evaluation with verified geographic coordinates and realistic hydrology.
