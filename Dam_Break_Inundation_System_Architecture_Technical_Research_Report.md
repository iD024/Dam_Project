# System Architecture & Technical Research Report
## Problem Statement 26161 — Dam Break Inundation Modelling Using Hydrodynamic Modelling of Any River

**Role perspective:** Principal Hydroinformatics Architect · Lead Geospatial Engineer · Full-Stack Systems Architect  
**Document status:** Implementation-ready reference architecture  
**Primary reference:** `Dam_Break_Flood_Simulation_AI_Product_Report(1).md` supplied with this task. The source document establishes the product intent: scenario-driven dam/river selection, automated data preparation, Delft3D/SPH execution, flood-depth/velocity/arrival outputs, GIS impact analysis, satellite comparison, exports, and AI assistance. fileciteturn0file0L8-L27  
**Research basis:** Deltares D-Flow FM documentation, DualSPHysics documentation/examples, Google Earth Engine Sentinel-1 documentation/tutorials, GDAL/PostGIS/Docker documentation, and open geospatial data-provider documentation.

> **Engineering disclaimer:** This architecture is suitable for software implementation and research/hackathon demonstration. It is **not** a substitute for a certified dam-break study, emergency action plan, or operational flood warning system. Breach parameters, terrain conditioning, boundary conditions, roughness and validation data must be reviewed by a hydrologist/hydraulic engineer before operational use.

---

# 0. Executive Technical Summary

Problem Statement 26161 calls for a generalized framework that can automatically prepare data, simulate a dam-break/flash-flood scenario with Smooth Particle Hydrodynamics and Delft3D, visualize and compare outputs, export SHP/KML, and support near-real-time flood analysis through Google Earth Engine. The supplied product report already frames the core platform as a decision-support engine rather than merely a website. fileciteturn0file0L32-L38

The implementation proposed here is a **job-oriented geospatial simulation platform** with six layers:

1. **Web GIS:** Next.js + TypeScript + MapLibre GL + deck.gl.
2. **API/orchestration:** FastAPI + Celery + Redis.
3. **Spatial/data platform:** PostgreSQL 16 + PostGIS + MinIO/S3.
4. **Physics execution:** D-Flow FM (Delft3D Flexible Mesh) CPU/cluster workers and DualSPHysics GPU workers.
5. **Earth observation/AI:** Google Earth Engine + PyTorch + Optuna/Bayesian optimisation.
6. **Result/export/validation:** xarray/rasterio/GeoPandas/GDAL + standardized flood products.

The architecture deliberately separates:

```text
PHYSICS PREDICTION          EARTH OBSERVATION
Delft3D / DualSPHysics  <-> Sentinel-1 / GEE
          |                     |
          +-------- comparison--+
                    |
             validation metrics
                    |
              calibration/AI
```

A major implementation rule is: **the product must not reimplement the hydrodynamic solver.** The application should generate model inputs, submit jobs, collect logs/status, parse native outputs, standardize them, and perform geospatial/impact analysis. This is consistent with the supplied architecture report. fileciteturn0file0L242-L281

---

# 1. Requirements Traceability

| Problem-statement requirement | Implementation |
|---|---|
| Generalized dam-break/river blockage framework | Canonical Scenario Contract + solver adapters |
| Sudden surge + HADR analysis | Breach model + time-dependent hydrodynamics + arrival-time/risk layers |
| Delft3D + SPH | D-Flow FM adapter + DualSPHysics CUDA adapter |
| Different datasets | Dataset registry + provenance + preprocessing DAG |
| Large data volumes | MinIO/object storage + chunked NetCDF/Zarr + COG GeoTIFF + vector tiling |
| Dashboard | Next.js/MapLibre/deck.gl |
| SHP/KML | GDAL/OGR export worker |
| Near-real-time GEE | Sentinel-1 change detection + flood mask validation |
| Indian demonstration | Mountainous + alluvial reference scenarios |

The supplied report recommends an initial MVP around one Indian dam/river, a complete physics path, standardized outputs, GIS visualization, satellite validation and then incremental SPH/AI features. fileciteturn0file0L2049-L2126

---

# 2. System-of-Systems Architecture

## 2.1 Logical architecture

```text
                                      +----------------------+
                                      |       USER/HADR      |
                                      +----------+-----------+
                                                 |
                                                 v
+--------------------------------------------------------------------------------+
|                               WEB EXPERIENCE                                   |
| Next.js / React / TypeScript / MapLibre GL / deck.gl                          |
| Scenario Builder | Job Monitor | Flood Timeline | Compare | Reports | Export |
+--------------------------------------+-----------------------------------------+
                                       |
                                 HTTPS / WebSocket
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                         APPLICATION / ORCHESTRATION                            |
| FastAPI                                                                         |
| Auth | Projects | Datasets | Scenarios | Simulations | Results | Validation    |
+-------------+----------------------+----------------------+---------------------+
              |                      |                      |
              v                      v                      v
     +----------------+       +-------------+       +-------------------+
     | Postgres 16    |       | Redis       |       | MinIO S3          |
     | + PostGIS      |       | broker      |       | DEM | NetCDF | TIF|
     | metadata/GIS   |       | + progress  |       | VTK | KML | logs |
     +----------------+       +------+------+       +-------------------+
                                      |
                                      v
                             +------------------+
                             | Celery workers   |
                             +--+-----+------+--+
                                |     |      |
              +-----------------+     |      +------------------+
              |                       |                         |
              v                       v                         v
   +-------------------+    +--------------------+    +----------------------+
   | D-Flow FM worker  |    | SPH CUDA worker    |    | GIS / EO worker      |
   | .mdu/.ext/.bc     |    | GenCase -> GPU ->  |    | GEE -> flood mask    |
   | NetCDF outputs    |    | PartVTK/IsoSurface |    | raster/vector ops    |
   +---------+---------+    +---------+----------+    +-----------+----------+
             |                        |                           |
             +------------+-----------+---------------------------+
                          |
                          v
                +-----------------------+
                | Result Normalization  |
                | COG/GeoTIFF/GeoJSON   |
                | metrics/manifest      |
                +-----------+-----------+
                            |
                 +----------+-----------+
                 |                      |
                 v                      v
        +-------------------+   +---------------------+
        | PostGIS impact    |   | AI/ML calibration   |
        | assets/intersect  |   | surrogate/QA        |
        +-------------------+   +---------------------+
                 \                      /
                  +----------+---------+
                             |
                             v
                      WEB GIS PRODUCTS
```

The overall shape follows the supplied data-flow concept but makes the job queue, object storage, solver adapters and normalized result store first-class components. fileciteturn0file0L1830-L1866

## 2.2 Deployment boundaries

**Stateless tier**

- Next.js application.
- FastAPI API replicas.
- WebSocket/SSE gateway if used separately.

**Stateful tier**

- PostgreSQL/PostGIS.
- Redis.
- MinIO.

**Compute tier**

- CPU solver workers for D-Flow FM.
- GPU workers for DualSPHysics.
- GIS/EO workers for rasterization, vectorization and GEE jobs.
- AI workers for calibration/training/inference.

This separation prevents long-running simulation jobs from blocking HTTP threads. The supplied report explicitly identifies simulations and heavy raster/AI operations as background workloads. fileciteturn0file0L2408-L2431

---

# 3. Canonical Data Model and Data Contracts

## 3.1 Design rule

Everything is organized around:

```text
Project
 ├── Dam
 ├── River
 ├── Datasets
 ├── Scenario
 │    ├── Breach
 │    ├── Hydrology
 │    ├── Terrain
 │    └── Numerical settings
 ├── Simulation Job(s)
 ├── Simulation Results
 ├── Observed Flood
 ├── Validation
 └── Exports
```

This is the same product-level mental model established in the supplied report. fileciteturn0file0L2499-L2527

## 3.2 Scenario contract

```json
{
  "schema_version": "1.0.0",
  "project_id": "01J...",
  "dam_id": "01J...",
  "river_id": "01J...",
  "domain": {
    "bbox": [78.0, 29.9, 78.4, 30.3],
    "crs": "EPSG:32644"
  },
  "terrain": {
    "dem_uri": "s3://flood/input/dem/cog.tif",
    "resolution_m": 10,
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
    "upstream_q_m3s": null,
    "downstream_bc": {
      "type": "discharge_timeseries",
      "uri": "s3://flood/input/hydro/bc.csv"
    }
  },
  "roughness": {
    "source": "landcover",
    "raster_uri": "s3://flood/input/roughness/n.tif",
    "default_manning_n": 0.04
  },
  "breach": {
    "type": "trapezoidal_progressive",
    "failure_mode": "overtopping",
    "start_s": 60,
    "formation_time_s": 180,
    "bottom_width_m": 80,
    "top_width_m": 110,
    "side_slope_hv": 1.0,
    "bottom_elevation_m": 760.0,
    "hydrograph_model": "weir_dynamic"
  },
  "solvers": ["dflowfm", "dualsphysics"],
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
  },
  "provenance": {
    "created_by": "user",
    "datasets": ["cop-dem-glo-30", "hydrorivers", "osm"]
  }
}
```

## 3.3 Result manifest

```json
{
  "simulation_id": "sim_01J...",
  "status": "completed",
  "solver": "dflowfm",
  "solver_version": "pinned-version",
  "scenario_hash": "sha256:...",
  "inputs": {
    "terrain": "s3://.../dem.tif",
    "roughness": "s3://.../n.tif",
    "forcing": "s3://.../bc.csv"
  },
  "products": {
    "max_depth": "s3://.../max_depth.tif",
    "max_velocity": "s3://.../max_velocity.tif",
    "arrival_time": "s3://.../arrival_time.tif",
    "flood_extent": "s3://.../flood_extent.geojson"
  },
  "metrics": {
    "peak_discharge_m3s": 0.0,
    "max_depth_m": 0.0,
    "max_velocity_ms": 0.0,
    "flood_area_km2": 0.0
  },
  "validation": {
    "observed_dataset_id": null,
    "iou": null,
    "csi": null,
    "fpr": null,
    "fnr": null
  }
}
```

---

# 4. Mathematical and Physical Formulations

# 4.1 D-Flow FM: 2D depth-averaged shallow-water equations

D-Flow FM solves depth-averaged 2D/3D shallow-water equations. The 2D equations given in Deltares technical material are expressed in conservative form as mass conservation plus momentum, including horizontal viscosity and bottom friction. citeturn953931search0turn953931search8

Define:

- \(\zeta(x,y,t)\): free-surface elevation.
- \(z_b(x,y)\): bed elevation.
- \(h=\zeta-z_b\): water depth.
- \(\mathbf{u}=(u,v)^T\): depth-averaged velocity.
- \(g\): gravitational acceleration.
- \(\nu_h\): horizontal eddy viscosity.
- \(f\): Coriolis parameter.
- \(\mathbf{u}^{\perp}=(-v,u)^T\).

## Continuity

\[
\frac{\partial h}{\partial t}+\nabla\cdot(h\mathbf{u})=0
\]

Expanded:

\[
\frac{\partial h}{\partial t}
+\frac{\partial(hu)}{\partial x}
+\frac{\partial(hv)}{\partial y}=0
\]

## Momentum

\[
\frac{\partial(h\mathbf{u})}{\partial t}
+\nabla\cdot(h\mathbf{u}\otimes\mathbf{u})
=-gh\nabla\zeta
+\nabla\cdot\left[\nu_hh\left(\nabla\mathbf{u}+\nabla\mathbf{u}^{T}\right)\right]
+\frac{\boldsymbol{\tau}_b}{\rho}
-hf\mathbf{u}^{\perp}
\]

Equivalent non-conservative momentum form is often written as:

\[
\frac{\partial\mathbf{u}}{\partial t}
+(\mathbf{u}\cdot\nabla)\mathbf{u}
=-g\nabla\zeta
+\frac{1}{h}\nabla\cdot\left[\nu_hh(\nabla\mathbf{u}+\nabla\mathbf{u}^{T})\right]
+\frac{\boldsymbol{\tau}_b}{\rho h}
-f\mathbf{u}^{\perp}
\]

D-Flow FM references give the same core structure; the exact sign convention for the Coriolis term depends on how \(\mathbf{u}^{\perp}\) is defined. citeturn953931search1

## Manning bed friction

For 2D surface-water applications it is useful to parameterize resistance with Manning \(n\). A standard acceleration form is:

\[
\mathbf{a}_f
=-g n^2\frac{|\mathbf{u}|\mathbf{u}}{h^{4/3}}
\]

and the corresponding depth-integrated friction term can be represented as:

\[
\frac{\boldsymbol{\tau}_b}{\rho}
=-g n^2\frac{|\mathbf{u}|\mathbf{u}}{h^{1/3}}
\]

because dividing the momentum equation by \(h\) gives the \(h^{-4/3}\) acceleration dependence.

D-Flow FM itself can parameterize friction using a Chezy coefficient and equivalent relations can be used to map Manning \(n\) into Chezy under a chosen convention. The platform should record **both the solver parameter and the conversion formula used**, not silently assume one. citeturn953931search0

## Coriolis

\[
\boldsymbol{a}_{cor}=-f\mathbf{u}^{\perp}
\]

with:

\[
f=2\Omega\sin\phi
\]

where \(\Omega\) is Earth rotation rate and \(\phi\) latitude.

For a small, short-lived dam-break event, Coriolis may be dynamically weak relative to gravity, inertia and friction. It should nevertheless remain configurable because it is part of the governing formulation requested by the problem.

## Horizontal eddy viscosity

The viscous stress contribution is:

\[
\nabla\cdot\left[\nu_hh(\nabla\mathbf{u}+\nabla\mathbf{u}^{T})\right]
\]

The system should support either a constant \(\nu_h\) or a spatial/solver-specific field if the chosen D-Flow FM setup exposes it.

## Flux form used by the numerical solver

For finite-volume discretization, cell-integrated conservation form is preferable:

\[
\frac{d}{dt}\int_\Omega h\,dA
+
\int_{\partial\Omega} h\mathbf{u}\cdot\mathbf{n}\,ds=0
\]

and:

\[
\frac{d}{dt}\int_\Omega h\mathbf{u}\,dA
+
\int_{\partial\Omega}h(\mathbf{u}\otimes\mathbf{u})\mathbf{n}\,ds
=
\int_\Omega \mathbf{S}\,dA
\]

where \(\mathbf{S}\) includes pressure/slope, friction, viscosity, Coriolis and other source terms.

D-Flow FM numerical descriptions use finite-volume methods and staggered arrangements; practical time stepping is constrained by a Courant stability criterion. Recent work using D-Flow FM reports dynamically controlled time steps based on the Courant criterion. citeturn953931search3

---

# 4.2 SPH / DualSPHysics formulation

DualSPHysics is a Lagrangian, mesh-free particle method. Each particle carries mass, position, velocity, density, pressure and auxiliary state. The supplied product report correctly identifies it as a mesh-free particle approach with local interactions. fileciteturn0file0L286-L310

## Continuous governing equations

Mass:

\[
\frac{D\rho}{Dt}=-\rho\nabla\cdot\mathbf{v}
\]

Momentum:

\[
\frac{D\mathbf{v}}{Dt}
=-\frac{1}{\rho}\nabla p
+\mathbf{g}
+\mathbf{f}_{visc}
+\mathbf{f}_{art}
+\mathbf{f}_{boundary}
\]

where the final terms capture physical/artificial dissipation and solid-boundary interactions.

## SPH kernel approximation

For a scalar field \(A\):

\[
A(\mathbf{x}_i)
\approx
\sum_j m_j\frac{A_j}{\rho_j}W_{ij}
\]

and a common gradient approximation is:

\[
\nabla A_i
\approx
\sum_j m_j\frac{A_j}{\rho_j}\nabla_iW_{ij}
\]

The particle support is limited by the kernel radius.

## Wendland C2 kernel

Let:

\[
q=\frac{r_{ij}}{h}
\]

with smoothing length \(h\). The Wendland C2 kernel used in common SPH implementations is:

\[
W(r,h)=\frac{\sigma_d}{h^d}
\left(1-\frac q2\right)^4(2q+1)
\qquad 0\le q<2
\]

and:

\[
W=0 \qquad q\ge2
\]

with:

\[
\sigma_2=\frac{7}{4\pi},
\qquad
\sigma_3=\frac{21}{16\pi}
\]

The normalization and compact support are documented in SPH references and implementations. citeturn690351search2turn690351search43

## Density summation

\[
\rho_i=\sum_jm_jW_{ij}
\]

An equivalent continuity form used in SPH implementations is:

\[
\frac{d\rho_i}{dt}
=\sum_jm_j(\mathbf{v}_i-\mathbf{v}_j)\cdot\nabla_iW_{ij}
\]

The latter form appears in established SPH libraries. citeturn690351search2

## Symmetric pressure force

A standard symmetric discretization is:

\[
\frac{d\mathbf{v}_i}{dt}
= -\sum_jm_j
\left(
\frac{p_i}{\rho_i^2}+
\frac{p_j}{\rho_j^2}
\right)\nabla_iW_{ij}
+\mathbf{g}+\mathbf{a}^{visc}_i+\mathbf{a}^{art}_i
\]

This pairwise symmetry is important for momentum conservation.

## Tait weakly-compressible EOS

DualSPHysics-style WCSPH uses a Tait-type EOS:

\[
p=B\left[\left(\frac{\rho}{\rho_0}\right)^\gamma-1\right]
\]

where:

\[
B=\frac{c_0^2\rho_0}{\gamma}
\]

and typically \(\gamma=7\) for water. The artificial sound speed \(c_0\) is selected sufficiently above expected flow velocities to constrain density variation. citeturn690351search0turn690351search41

Engineering rule for the platform:

```text
Choose c0 such that Mach number M = Umax / c0 is small.
Then monitor max |rho-rho0| / rho0.
Reject/flag runs with excessive compressibility.
```

## Monaghan artificial viscosity

For approaching particles \(\mathbf{v}_{ij}\cdot\mathbf{r}_{ij}<0\):

\[
\Pi_{ij}
=
\frac{-\alpha\bar c_{ij}\phi_{ij}+\beta\phi_{ij}^2}
{\bar\rho_{ij}}
\]

with:

\[
\phi_{ij}
=
\frac{h_{ij}(\mathbf{v}_{ij}\cdot\mathbf{r}_{ij})}
{r_{ij}^2+\epsilon^2}
\]

and:

\[
\bar c_{ij}=\frac{c_i+c_j}{2},
\quad
\bar\rho_{ij}=\frac{\rho_i+\rho_j}{2}
\]

otherwise \(\Pi_{ij}=0\).

The acceleration is:

\[
\mathbf{a}^{art}_i
=-\sum_jm_j\Pi_{ij}\nabla_iW_{ij}
\]

This is the classical Monaghan form documented by SPH references. citeturn690351search2turn690351search5

## SPH timestep controls

A production adapter should expose and log:

- particle spacing \(dp\),
- smoothing length \(h\),
- artificial sound speed \(c_0\),
- CFL factor,
- viscous timestep bound,
- force/acceleration timestep bound,
- output interval,
- GPU device ID.

The platform must never advertise a SPH run as physically equivalent to D-Flow FM solely because both produce a flood polygon. A solver comparison is a **verification/benchmark exercise**, not a claim of interchangeability.

---

# 4.3 Breach geometry and breach hydrograph

Breach modelling introduces the largest epistemic uncertainty in a dam-break scenario. The system therefore supports multiple empirical methods and stores the selected method and parameter ranges with the scenario.

## Froehlich 2008 average breach width

For embankment dams:

\[
B_{ave}=0.27K_0V_w^{0.32}h_b^{0.04}
\]

where:

- \(B_{ave}\) = average final breach width (m)
- \(V_w\) = reservoir volume at failure (m³)
- \(h_b\) = final breach height (m)
- \(K_0\) = failure-mode coefficient; one common representation uses 1.3 for overtopping and 1.0 for piping.

Froehlich also gives a breach formation-time relation:

\[
t_f=63.2\sqrt{\frac{V_w}{gh_b^2}}
\]

The original 2008 work was based on a database of 74 embankment-dam failures and explicitly addresses uncertainty in breach width, side slope and formation time. citeturn250464search2turn250464search5

## Froehlich 1995 reference form

A frequently cited earlier regression is:

\[
B_{ave}=0.1803K_0V_w^{0.32}h_b^{0.19}
\]

\[
t_f=0.00254V_w^{0.53}h_b^{-0.90}
\]

These empirical forms are not interchangeable; the scenario record should state which edition is used. citeturn250464search1

## MacDonald–Langridge-Monopolis

For earthfill dams:

\[
V_{eroded}=0.0261(V_{out}h_w)^{0.769}
\]

\[
t_f=0.0179V_{eroded}^{0.364}
\]

For earthfill with clay core / rockfill variants, a commonly cited relation is:

\[
V_{eroded}=0.00348(V_{out}h_w)^{0.852}
\]

The original formulation relates eroded embankment volume to a breach-formation factor and derives formation time from the eroded volume. citeturn250464search0turn250464search4

A corresponding trapezoidal bottom-width relation can be represented as:

\[
W_b =
\frac{V_{eroded}-h_b^2(CZ_b+h_bZ_bZ_3/3)}
{h_b(C+h_bZ_3/2)}
\]

where the source formulation defines the embankment/breach slope terms; exact symbol conventions must be carried into code and metadata rather than inferred silently. citeturn250464search5

## Peak breach discharge

For an abrupt breach, a simplified hydraulic upper-bound style estimate can use broad-crested/free-weir or critical-flow relations, but the platform should prefer a solver-specific dynamic breach hydrograph whenever the chosen solver supports it.

A published empirical relation often referenced alongside MacDonald-Langridge is:

\[
Q_p=1.154(V_wH_w)^{0.412}
\]

where the exact units and dataset applicability must be checked against the source implementation before production use. citeturn250464search3

## Breach parameter uncertainty contract

Do not store only one number:

```json
{
  "method": "froehlich_2008",
  "breach_width_m": {
    "mean": 102.4,
    "p05": 80.2,
    "p95": 132.7
  },
  "formation_time_s": {
    "mean": 182,
    "p05": 90,
    "p95": 420
  },
  "side_slope_hv": {
    "mean": 1.0,
    "p05": 0.5,
    "p95": 2.0
  }
}
```

This directly enables ensemble scenarios and Monte Carlo uncertainty analysis, which is preferable to presenting a single deterministic flood boundary as exact.

---

# 5. End-to-End Input Processing and Data Lineage

## 5.1 Raw inputs

### Terrain

Primary recommended open DEM: **Copernicus DEM GLO-30** where access and licensing requirements are satisfied. Current Copernicus Data Space documentation describes global 30 m coverage and programmatic access via OData/S3, while the 30 m access policy has recently moved to authorized CCM-user categories. citeturn536822search3turn536822search5

Fallbacks:

- SRTM 30 m.
- Copernicus DEM GLO-90 for broad screening.
- Higher-resolution authoritative/local DEM where available.

### River network

HydroRIVERS is useful as a generalized river-network prior; the HydroRIVERS network derives from HydroSHEDS and represents river segments above stated catchment/flow criteria. citeturn953931search9

### Exposure

OpenStreetMap via Overpass can provide roads, buildings, bridges, schools, hospitals and other tagged objects. The Overpass API is intended for custom, read-only data extraction by spatial extent/tag filters. citeturn536822search9turn536822search10

### Hydrology

India-WRIS should be treated as a candidate national hydrology source. Because archive access and station-specific availability may vary, the ingestion layer must record:

```text
source_url
station_id
measurement_type
unit
sampling_interval
start_time
end_time
quality_flag
retrieval_time
```

The product must not fabricate a discharge series when the required observation is unavailable.

## 5.2 Normalization pipeline

```text
RAW DATASET
    |
    +--> checksum
    +--> metadata extraction
    +--> CRS detection
    +--> vertical datum metadata
    +--> no-data characterization
    |
    v
CANONICAL INGESTION
    |
    +--> reprojection to local metric CRS
    +--> AOI clipping
    +--> unit normalization
    +--> spatial-index registration
    |
    v
MODEL DATASET
    |
    +--> terrain.tif / terrain.zarr
    +--> river.geojson
    +--> boundaries.pli/.ext/.bc
    +--> roughness.tif
    |
    v
SOLVER PACKAGE
```

## 5.3 Data lineage record

Each produced dataset gets:

```json
{
  "dataset_id": "ds_123",
  "parent_dataset_ids": ["raw_45", "raw_46"],
  "source_provider": "Copernicus",
  "source_product": "COP-DEM-GLO-30",
  "retrieved_at": "2026-09-06T00:00:00Z",
  "checksum_sha256": "...",
  "crs_in": "EPSG:4326",
  "crs_out": "EPSG:32644",
  "vertical_datum": "unknown",
  "processing": [
    "clip_aoi",
    "warp_bilinear",
    "river_burn_1m",
    "write_cog"
  ],
  "software": {
    "gdal": "pinned",
    "rasterio": "pinned"
  }
}
```

This implements the supplied report's explicit reproducibility/data-lineage rule. fileciteturn0file0L2331-L2374

---

# 6. Simulation Domain Construction

## 6.1 Domain selection

Default algorithm:

1. Buffer dam location by a configurable upstream radius.
2. Trace downstream river segments using HydroRIVERS plus local river geometry.
3. Expand perpendicular to channel until terrain-gradient/flow-accumulation criteria identify the floodplain.
4. Optionally extend downstream to a user-defined boundary.
5. Clip every input to the domain.

## 6.2 DEM conditioning

Do not indiscriminately fill all sinks in a dam-break hydraulic model. Artificially filling depressions can remove real storage basins and change the flood extent.

Recommended conditioning steps:

```text
1. Validate nodata islands.
2. Remove obvious acquisition artifacts.
3. Reproject to metric CRS.
4. Resample only when justified.
5. Optional river burn using known surveyed thalweg.
6. Preserve bridges/embankments where reliable geometry exists.
7. Generate slope and roughness derivatives.
8. Keep original DEM immutable.
```

## 6.3 Roughness raster

Map land-cover classes to candidate Manning values:

| Class | Candidate n |
|---|---:|
| Open water | 0.025–0.040 |
| Managed agriculture | 0.035–0.060 |
| Dense forest | 0.080–0.150 |
| Rural settlement | 0.060–0.120 |
| Dense urban | 0.080–0.160 |
| Main channel | 0.025–0.045 |

These are **initial ranges**, not universal constants. The supplied report also cautions that roughness values must be calibrated for the chosen model. fileciteturn0file0L507-L522

Store:

```text
landcover_code
manning_n
source
confidence
calibrated
calibration_run_id
```

---

# 7. D-Flow FM Orchestration

## 7.1 File model

The implementation must account for modern D-Flow FM naming rather than blindly applying older Delft3D legacy conventions.

Current hydrolib-core documentation describes the `.ext` file as the external-forcing definition and references a modern `.bc` forcing model. Boundary locations are carried through polyline/support-point files, typically `.pli`. citeturn418439search0turn418439search2

Therefore the adapter should generate approximately:

```text
case/
  model.mdu
  domain_net.nc
  domain_dep.nc / terrain data
  open_boundary.pli
  boundary.bc
  model.ext
  roughness.*
  breach.*
  output/
```

Legacy `.bnd/.bct` terms can appear in historical documentation and conversions; the adapter should expose a `file_schema_version` rather than assume the same format for every installation. citeturn418439search17

## 7.2 Grid generation

### Preferred production path

Use an existing D-Flow FM-compatible network-generation toolchain, with Python controlling it rather than attempting to author NetCDF topology by hand.

Grid strategy:

```text
River corridor: finer cells
Floodplain: coarser cells
Structures/breach: localized refinement
Far-field: progressively coarser
```

The supplied product report already recommends multiple resolution modes and notes that actual resolution depends on study area, terrain and compute. fileciteturn0file0L2019-L2044

## 7.3 Bathymetry interpolation

Pseudo-implementation that is intentionally **executable scaffolding** around an established grid tool rather than a fake solver:

```python
from pathlib import Path
import subprocess


def run_grid_generator(exe: str, config: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(
        [exe, str(config)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"Grid generation failed ({cp.returncode})\\nSTDOUT:\\n{cp.stdout}\\nSTDERR:\\n{cp.stderr}"
        )
```

For terrain interpolation, preserve the raster's native values and use interpolation appropriate for the variable:

- bilinear for smoothly varying bed elevation;
- nearest for categorical roughness;
- conservative/area-aware remapping where justified.

## 7.4 Boundary file generation

A modern external-forcing file can connect a boundary quantity to a `.pli` support geometry and a `.bc` forcing file. Hydrolib-core exposes this structure programmatically. citeturn418439search0

Example conceptual `.bc`:

```ini
[forcing]
Name = upstream_discharge
Function = timeseries
Time-interpolation = linear
Quantity = time
Unit = minutes since 2000-01-01
Quantity = dischargebnd
Unit = m3/s
0.0  1200.0
60.0 1400.0
120.0 1800.0
180.0 2500.0
```

Example conceptual `.ext`:

```ini
[boundary]
quantity = dischargebnd
locationfile = upstream.pli
forcingfile = boundary.bc
```

The exact MDU keys must be generated for the pinned D-Flow FM version and verified using its own schema/manual.

## 7.5 Programmatic execution

```python
import subprocess
from pathlib import Path


def run_dflowfm(executable: str, mdu: Path, workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [executable, str(mdu)]
    proc = subprocess.run(
        cmd,
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        check=False,
    )
    (workdir / "solver.log").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"D-Flow FM failed: rc={proc.returncode}")
```

In the production worker use `subprocess.Popen` with line streaming to Redis/Postgres for progress events.

## 7.6 Parsing NetCDF outputs

The result parser should use xarray. `xarray.open_dataset` supports NetCDF and can use Dask chunking for large datasets. citeturn860744search2

```python
import xarray as xr


def parse_map(path: str) -> xr.Dataset:
    return xr.open_dataset(path, chunks="auto")


def inspect_variables(path: str) -> dict:
    ds = xr.open_dataset(path, chunks="auto")
    return {
        "dimensions": dict(ds.sizes),
        "variables": list(ds.data_vars),
        "coords": list(ds.coords),
    }
```

The parser should not hard-code variable names without a compatibility map because D-Flow FM output variable names can vary by model configuration/version.

```python
FIELD_ALIASES = {
    "water_depth": ["waterdepth", "waterdepth_m", "depth"],
    "water_level": ["waterlevel", "s1"],
    "velocity_x": ["ucx", "u", "velocity_x"],
    "velocity_y": ["ucy", "v", "velocity_y"],
}
```

## 7.7 Product derivation

For each time slice:

```text
h_t(x,y)
|-> flood_mask_t = h_t > dry_threshold
|-> speed_t = sqrt(u_t^2 + v_t^2)
|-> arrival_time = first t where h_t > threshold
|-> max_depth = max_t h_t
|-> max_speed = max_t speed_t
|-> duration = count_t(h_t > threshold) * output_interval
```

---

# 8. DualSPHysics Orchestration

## 8.1 Pipeline

```text
DEM GeoTIFF
   |
   +--> resample / crop / vertical shift
   |
   +--> terrain mesh / STL geometry
   |
   +--> GenCase XML
   |
   v
GenCase
   |
   v
Initial BI4 / boundary particles
   |
   v
DualSPHysics GPU
   |
   v
Part_XXXX.bi4
   |
   +--> PartVTK
   +--> IsoSurface
   |
   v
VTK / structured grid
   |
   v
Depth/velocity rasters
```

DualSPHysics example cases explicitly show `GenCase` followed by the GPU executable, and post-processing through `PartVTK`; their tooling also includes `IsoSurface`. citeturn312142search1turn312142search3turn312142search6

## 8.2 Terrain-to-STL strategy

The implementation should not convert a huge raw DEM directly into an unbounded triangle mesh. First tile/clip and simplify.

```text
DEM COG
  -> AOI crop
  -> resampling (choose dp-compatible spacing)
  -> void repair
  -> local coordinate transform
  -> triangulation/grid surface
  -> STL
```

Store the STL as a versioned artifact:

```text
terrain_{sha}.stl
terrain_{sha}.json
```

with:

```json
{
  "source_dem_sha256": "...",
  "resolution_m": 2.0,
  "vertical_units": "m",
  "origin": [x0, y0, z0],
  "triangle_count": 123456
}
```

## 8.3 GenCase XML

The adapter should generate the case definition rather than hand-authoring one massive XML template.

```python
from xml.etree.ElementTree import Element, SubElement, ElementTree


def write_case_xml(path: str, particle_spacing: float, gravity: tuple[float, float, float]):
    root = Element("case")
    constants = SubElement(root, "constants")
    SubElement(constants, "particle_spacing", value=str(particle_spacing))
    SubElement(constants, "gravity", x=str(gravity[0]), y=str(gravity[1]), z=str(gravity[2]))
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
```

**Important:** the real schema must be generated from the pinned DualSPHysics version's XML example/template, not from this minimal scaffold. The architecture treats the versioned example case as the schema authority.

## 8.4 GPU execution

Example Linux pattern:

```bash
GenCase_linux64 case_Def case_out/case -save:all
DualSPHysics5.4_linux64 -gpu case_out/case case_out
```

The DualSPHysics HPC example shows the same general execution sequence. citeturn312142search3

In Docker, reserve one NVIDIA GPU for the worker. Docker Compose supports device reservations using the `deploy.resources.reservations.devices` syntax. citeturn860744search1

## 8.5 PartVTK and IsoSurface

PartVTK can generate VTK/CSV/stats products and supports selecting particle types and variables. citeturn312142search0

Example:

```bash
PartVTK -dirdata /work/case_out/data \
        -savevtk /work/case_out/particles/PartFluid \
        -onlytype:-all,fluid \
        -vars:+idp,+vel,+rhop,+press,+vor,+energy

IsoSurface -dirin /work/case_out/data \
          -saveiso /work/case_out/surface/Slices \
          -onlytype:+fluid
```

The exact option set must be checked against the pinned version's help output. The documentation explicitly supports interpolation to a Cartesian mesh using `-distnode_dp` or `-distnode`, which is useful for producing a grid-based result product. citeturn312142search6

## 8.6 SPH depth rasterization

The normalized product needs a raster in the same CRS/grid as the D-Flow FM comparison domain.

```text
VTK surface/particles
   -> extract z_surface
   -> rasterize to target grid
   -> depth = z_surface - z_bed
   -> clip < 0
   -> write COG GeoTIFF
```

Where a direct surface reconstruction yields only a water-surface field, depth must be computed against the **same terrain reference** used to construct the boundary.

---

# 9. Solver Comparison Protocol

## 9.1 Scientific control variables

To compare solvers fairly, hold fixed:

- same DEM/terrain;
- same dam geometry;
- same initial reservoir level/storage;
- same breach width/depth/time law;
- same gravity;
- same roughness equivalent as far as each solver permits;
- same output threshold;
- same simulation end time;
- same reporting CRS/grid.

## 9.2 Metrics

### Conservation error

\[
E_M(t)=\frac{|V(t)-V_0-\int_0^t(Q_{in}-Q_{out})d\tau|}{V_0+\epsilon}
\]

### Peak discharge error

\[
E_Q=\frac{|Q_{p,1}-Q_{p,2}|}{\max(|Q_{p,1}|,\epsilon)}
\]

### Flood extent IoU

\[
IoU=\frac{|F_A\cap F_B|}{|F_A\cup F_B|}
\]

### Hausdorff/boundary distance

Compare flood-boundary geometry after placing both outputs on the same raster/vector representation.

## 9.3 Benchmark matrix

| Criterion | D-Flow FM | DualSPHysics | Recommended use |
|---|---|---|---|
| Large floodplain | Excellent | Expensive | D-Flow FM |
| Near-field breach jet | Good depending on mesh | Strong candidate | SPH validation/research |
| Free-surface/shock complexity | Good with appropriate FV setup | Strong local detail potential | SPH near-field |
| Long 0–50 km routing | Efficient | Potentially costly | D-Flow FM |
| GPU acceleration | Configuration dependent | Core strength | SPH |
| Unstructured terrain-following domain | Native strength | Boundary mesh/particle workflow | D-Flow FM |
| Automated generalized web service | High | High but heavier GPU infra | Both through adapters |
| Best hackathon role | Primary/far-field | Comparative/near-field | Hybrid |

The report supplied with the task already recommends treating Delft3D and SPH as two approaches that can be run on the same scenario and compared. fileciteturn0file0L231-L240

## 9.4 Near-field/far-field architecture

```text
DAM / BREACH
  |
  +--> 0–5 km: high-resolution SPH research domain
  |
  +--> 0–5 km or transition zone: D-Flow FM fine mesh
  |
  +--> >5 km: D-Flow FM floodplain routing
```

The 0–5 km / >5 km split is a **product benchmark convention**, not a physical law. The transition distance should be scenario-dependent.

---

# 10. Google Earth Engine Near-Real-Time Flood Engine

## 10.1 Crucial Sentinel-1 processing fact

Earth Engine's Sentinel-1 GRD ingestion already includes border-noise removal, thermal-noise removal, radiometric calibration and terrain correction as part of the ingestion pipeline. Therefore the application should **not pretend to repeat those upstream corrections on the ingested GRD image**. Instead:

```text
GEE Sentinel-1 GRD
  -> use already-corrected GRD backscatter
  -> optional application-level speckle filtering
  -> temporal baseline
  -> ratio / log-ratio
  -> adaptive threshold
  -> morphological cleanup
  -> flood mask
```

Google documents these Sentinel-1 preprocessing stages and the GRD bands including VV/VH/angle. citeturn953931search2turn596341search12

## 10.2 Sentinel-1 collection

Use:

```text
COPERNICUS/S1_GRD
```

Filter by:

- AOI;
- date range;
- instrument mode (`IW` for most land cases);
- polarization VV and/or VH;
- orbit direction where temporal comparability requires it.

Google's Sentinel-1 documentation demonstrates filtering by polarization and acquisition metadata. citeturn596341search13

## 10.3 Refined Lee implementation

Earth Engine does not provide a one-line built-in `refinedLee()` function. Implement the filter as an explicit local-statistics transform.

A production implementation should:

1. Create a local mean/variance estimator.
2. Compute directionality masks.
3. Estimate local noise variance.
4. Compute the adaptive weight.
5. Replace only the high-variance component.
6. Keep the output in linear power before log transformation.

For maintainability, keep this in its own `sar_filters.py`/GEE script module rather than embedding it in API code.

## 10.4 Log-ratio change detection

Let \(B\) be the pre-flood baseline and \(F\) the flood observation in linear backscatter.

Ratio:

\[
R=\frac{F}{B+\epsilon}
\]

Log-ratio in dB:

\[
L=10\log_{10}(R)
\]

A flood candidate can be defined for darkening cases by:

\[
L<T
\]

The threshold should be adaptive, not a universal fixed value.

## 10.5 Otsu thresholding

Given histogram probabilities \(p_i\), maximize between-class variance:

\[
\sigma_b^2(t)=
\frac{[\mu_T\omega(t)-\mu(t)]^2}
{\omega(t)[1-\omega(t)]}
\]

where \(\omega(t)\) is cumulative class probability and \(\mu(t)\) the cumulative mean.

The GEE implementation can approximate the histogram from an AOI with `reduceRegion(... ee.Reducer.histogram(...))` and run Otsu in server-side expressions or return histogram bins for client-side thresholding where scale limits permit.

## 10.6 Production Python GEE script

```python
import ee

PROJECT = "YOUR_EE_PROJECT"
ee.Initialize(project=PROJECT)


def get_s1(aoi, start, end, orbit=None):
    c = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    )
    if orbit is not None:
        c = c.filter(ee.Filter.eq("orbitProperties_pass", orbit))
    return c


def to_linear(img):
    return ee.Image(10).pow(img.divide(10.0))


def to_db(img):
    return ee.Image(img).max(1e-8).log10().multiply(10.0)


def median_composite(collection):
    return collection.median()


def otsu_from_histogram(hist_dict):
    # Kept as explicit Python for deterministic post-retrieval thresholding.
    counts = hist_dict["histogram"]
    means = hist_dict["bucketMeans"]
    total = float(sum(counts))
    sum_total = sum(c * m for c, m in zip(counts, means))
    weight_b = 0.0
    sum_b = 0.0
    best_var = -1.0
    best_threshold = means[0]

    for c, m in zip(counts, means):
        weight_b += c
        if weight_b == 0 or weight_b == total:
            continue
        sum_b += c * m
        w_f = total - weight_b
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / w_f
        var_between = weight_b * w_f * (mean_b - mean_f) ** 2
        if var_between > best_var:
            best_var = var_between
            best_threshold = m
    return best_threshold


def detect_flood(aoi, before_start, before_end, flood_start, flood_end):
    before = median_composite(get_s1(aoi, before_start, before_end)).select("VV")
    flood = median_composite(get_s1(aoi, flood_start, flood_end)).select("VV")

    # Linear-domain ratio, then convert to dB.
    ratio_db = to_db(to_linear(flood).divide(to_linear(before)))

    hist = ratio_db.reduceRegion(
        reducer=ee.Reducer.histogram(maxBuckets=256),
        geometry=aoi,
        scale=10,
        bestEffort=True,
        maxPixels=1e8,
    ).get("VV")

    # Pull histogram once for adaptive thresholding.
    hist_info = ee.Dictionary(hist).getInfo()
    threshold = otsu_from_histogram(hist_info)

    flood_mask = ratio_db.lt(threshold)

    # Morphological cleanup.
    flood_mask = (
        flood_mask
        .focal_max(radius=1, units="pixels")
        .focal_min(radius=1, units="pixels")
        .selfMask()
    )
    return flood_mask, threshold


if __name__ == "__main__":
    aoi = ee.Geometry.Rectangle([78.0, 29.9, 78.4, 30.3])
    mask, threshold = detect_flood(
        aoi,
        "2021-01-01", "2021-02-01",
        "2021-02-08", "2021-02-15",
    )
    print("Otsu threshold:", threshold)
    print(mask.getInfo())
```

Authentication for unattended environments should use an appropriate service account/default credentials setup. Google currently documents ADC/service-account patterns for Earth Engine applications. citeturn596341search0turn596341search7

**Production note:** the script above intentionally contains the complete processing shape but leaves the refined-Lee transform as a separately testable function; this avoids shipping an unverified one-line approximation as a supposedly validated speckle filter.

---

# 11. Satellite Validation Engine

## 11.1 Common grid

Predicted and observed flood masks must be reprojected to an identical evaluation grid before comparison.

```text
predicted depth raster
       |
       +--> threshold
       +--> reproject
       +--> pixel grid P

satellite flood mask
       |
       +--> reproject
       +--> pixel grid P
```

## 11.2 Confusion matrix

For binary flood classification:

- TP = predicted flooded & observed flooded.
- FP = predicted flooded & observed dry.
- FN = predicted dry & observed flooded.
- TN = predicted dry & observed dry.

## 11.3 Critical Success Index / Threat Score

\[
CSI=\frac{TP}{TP+FP+FN}
\]

## 11.4 IoU

For binary masks IoU is algebraically the same as CSI:

\[
IoU=\frac{|P\cap O|}{|P\cup O|}
=\frac{TP}{TP+FP+FN}
\]

The application may display both names because disaster-management literature commonly uses both.

## 11.5 False-positive / overprediction rate

Two variants exist; define the denominator explicitly in the product:

\[
FPR=\frac{FP}{FP+TN}
\]

Flood-area overprediction relative to observed flooded area:

\[
OverPred=\frac{FP}{TP+FN}
\]

## 11.6 False-negative / underprediction rate

\[
FNR=\frac{FN}{FN+TP}
\]

Flood-area underprediction relative to observed flood area:

\[
UnderPred=\frac{FN}{TP+FN}
\]

## 11.7 Python implementation

```python
import numpy as np


def binary_metrics(pred: np.ndarray, obs: np.ndarray) -> dict:
    pred = pred.astype(bool)
    obs = obs.astype(bool)

    tp = np.count_nonzero(pred & obs)
    fp = np.count_nonzero(pred & ~obs)
    fn = np.count_nonzero(~pred & obs)
    tn = np.count_nonzero(~pred & ~obs)

    denom = tp + fp + fn
    csi = tp / denom if denom else 1.0
    iou = csi
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0

    return {
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "csi": float(csi), "iou": float(iou),
        "fpr": float(fpr), "fnr": float(fnr),
        "overprediction": float(fp / (tp + fn)) if (tp + fn) else 0.0,
        "underprediction": float(fn / (tp + fn)) if (tp + fn) else 0.0,
    }
```

---

# 12. Full PostgreSQL 16 + PostGIS Schema

PostGIS recommends GiST spatial indexes for geometry and shows `CREATE INDEX ... USING GIST (geom)` as the standard pattern. citeturn860744search4turn860744search8

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE scenario_status AS ENUM ('draft','validated','queued','running','completed','failed','cancelled');
CREATE TYPE solver_type AS ENUM ('dflowfm','dualsphysics');

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    dam_type TEXT,
    crest_elevation_m DOUBLE PRECISION,
    height_m DOUBLE PRECISION,
    reservoir_area_m2 DOUBLE PRECISION,
    reservoir_storage_m3 DOUBLE PRECISION,
    geom geometry(Geometry, 4326) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX dams_geom_gix ON dams USING GIST (geom);
CREATE INDEX dams_project_idx ON dams(project_id);

CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dam_id UUID REFERENCES dams(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    scenario_version INTEGER NOT NULL DEFAULT 1,
    status scenario_status NOT NULL DEFAULT 'draft',
    engine_config JSONB NOT NULL,
    scenario_hash TEXT,
    domain geometry(Polygon, 4326),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX scenarios_domain_gix ON scenarios USING GIST (domain);
CREATE INDEX scenarios_project_idx ON scenarios(project_id);

CREATE TABLE simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    solver solver_type NOT NULL,
    solver_version TEXT NOT NULL,
    status scenario_status NOT NULL DEFAULT 'queued',
    celery_task_id TEXT,
    progress_pct NUMERIC(5,2) NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    exit_code INTEGER,
    log_uri TEXT,
    work_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX simulations_scenario_idx ON simulations(scenario_id);
CREATE INDEX simulations_status_idx ON simulations(status);

CREATE TABLE simulation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    product_type TEXT NOT NULL,
    object_uri TEXT NOT NULL,
    media_type TEXT NOT NULL,
    crs_epsg INTEGER,
    min_value DOUBLE PRECISION,
    max_value DOUBLE PRECISION,
    pixel_size_x DOUBLE PRECISION,
    pixel_size_y DOUBLE PRECISION,
    bbox geometry(Polygon, 4326),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX simulation_results_bbox_gix ON simulation_results USING GIST (bbox);
CREATE INDEX simulation_results_sim_idx ON simulation_results(simulation_id);

CREATE TABLE exposure_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    name TEXT,
    source TEXT,
    osm_id TEXT,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Geometry, 4326) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX exposure_assets_geom_gix ON exposure_assets USING GIST (geom);
CREATE INDEX exposure_assets_type_idx ON exposure_assets(asset_type);

CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    dataset_type TEXT NOT NULL,
    provider TEXT,
    source_uri TEXT,
    object_uri TEXT,
    checksum_sha256 TEXT,
    crs_epsg INTEGER,
    bbox geometry(Polygon, 4326),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX datasets_bbox_gix ON datasets USING GIST (bbox);

CREATE TABLE observed_floods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    acquisition_time TIMESTAMPTZ,
    raster_uri TEXT,
    vector_uri TEXT,
    mask geometry(MultiPolygon, 4326),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX observed_floods_mask_gix ON observed_floods USING GIST (mask);

CREATE TABLE validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    observed_flood_id UUID NOT NULL REFERENCES observed_floods(id) ON DELETE CASCADE,
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 12.1 Impact query examples

Affected assets:

```sql
SELECT a.id, a.name, a.asset_type
FROM exposure_assets a
JOIN simulation_results r
  ON r.simulation_id = $1
WHERE r.product_type = 'flood_extent'
  AND ST_Intersects(a.geom, ST_GeomFromGeoJSON($2));
```

Road length affected:

```sql
SELECT SUM(ST_Length(ST_Intersection(r.geom, f.geom)::geography)) / 1000.0 AS km_affected
FROM road_assets r
JOIN flood_polygons f ON ST_Intersects(r.geom, f.geom)
WHERE f.simulation_id = $1;
```

---

# 13. FastAPI Backend Blueprint

## 13.1 Pydantic models

```python
from enum import Enum
from pydantic import BaseModel, Field


class Solver(str, Enum):
    dflowfm = "dflowfm"
    dualsphysics = "dualsphysics"


class Breach(BaseModel):
    type: str
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    formation_time_s: float = Field(gt=0)


class SimulationRunRequest(BaseModel):
    scenario_id: str
    solvers: list[Solver] = [Solver.dflowfm]
    async_mode: bool = True


class SimulationRunResponse(BaseModel):
    simulation_ids: list[str]
    status: str
```

## 13.2 Celery setup

```python
from celery import Celery

celery_app = Celery(
    "flood_platform",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)
celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 86400
```

## 13.3 Simulation task

```python
from uuid import UUID

@celery_app.task(bind=True, name="simulation.run")
def run_simulation_task(self, simulation_id: str):
    sim = repo.get_simulation(UUID(simulation_id))
    try:
        repo.mark_running(UUID(simulation_id))
        self.update_state(state="RUNNING", meta={"progress": 5, "phase": "prepare"})

        workdir = prepare_case(sim)
        self.update_state(state="RUNNING", meta={"progress": 20, "phase": "solver"})

        execute_solver(sim.solver, workdir)
        self.update_state(state="RUNNING", meta={"progress": 70, "phase": "parse"})

        products = normalize_results(sim, workdir)
        repo.save_products(UUID(simulation_id), products)
        impact_analysis(sim, products)
        repo.mark_completed(UUID(simulation_id))
        return {"simulation_id": simulation_id, "progress": 100}
    except Exception as exc:
        repo.mark_failed(UUID(simulation_id), str(exc))
        raise
```

## 13.4 POST /api/v1/simulations/run

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1")


@router.post("/simulations/run", response_model=SimulationRunResponse, status_code=202)
def run(req: SimulationRunRequest):
    scenario = repo.get_scenario(req.scenario_id)
    if scenario is None:
        raise HTTPException(404, "Scenario not found")

    validate_scenario(scenario)

    ids = []
    for solver in req.solvers:
        sim = repo.create_simulation(
            scenario_id=req.scenario_id,
            solver=solver.value,
        )
        task = run_simulation_task.delay(str(sim.id))
        repo.attach_task_id(sim.id, task.id)
        ids.append(str(sim.id))

    return SimulationRunResponse(simulation_ids=ids, status="queued")
```

## 13.5 GET /status

```python
from fastapi import HTTPException


@router.get("/simulations/{simulation_id}/status")
def status(simulation_id: str):
    sim = repo.get_simulation(simulation_id)
    if sim is None:
        raise HTTPException(404, "Simulation not found")
    return {
        "id": str(sim.id),
        "status": sim.status,
        "progress": sim.progress_pct,
        "solver": sim.solver,
        "started_at": sim.started_at,
        "finished_at": sim.finished_at,
    }
```

## 13.6 WebSocket status stream

```python
from fastapi import WebSocket


@router.websocket("/simulations/{simulation_id}/events")
async def simulation_events(websocket: WebSocket, simulation_id: str):
    await websocket.accept()
    try:
        async for event in redis_event_stream(f"simulation:{simulation_id}"):
            await websocket.send_json(event)
    except Exception:
        await websocket.close()
```

## 13.7 Export endpoint

```python
@router.get("/simulations/{simulation_id}/export")
def export(simulation_id: str, format: str):
    if format not in {"shp", "kml"}:
        raise HTTPException(400, "format must be shp or kml")
    sim = repo.get_simulation(simulation_id)
    if sim is None:
        raise HTTPException(404, "Simulation not found")
    job = export_task.delay(simulation_id, format)
    return {"task_id": job.id, "status": "queued"}
```

**Why 202/asynchronous?** Simulations can last minutes/hours, and the supplied product report explicitly requires a background-job architecture rather than blocking HTTP requests. fileciteturn0file0L1644-L1686

---

# 14. GIS Export Engine

## 14.1 Flood-depth classes

Required classes:

```text
H0: h <= 0.5 m
H1: 0.5 < h <= 1.5 m
H2: 1.5 < h <= 3.0 m
H3: h > 3.0 m
```

The user requested thresholds `h > 0.5 m`, `h > 1.5 m`, `h > 3.0 m`; the exporter should preserve the continuous depth raster and additionally generate these hazard-class vectors.

## 14.2 Raster classification + polygonization

GDAL `gdal_polygonize` generates polygons from connected regions of equal raster values. citeturn860744search6

Python implementation:

```python
from pathlib import Path
import subprocess
import tempfile


def export_depth_classes(depth_tif: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    classes = [
        ("gt_0_5m", "-0.5", "1"),
        ("gt_1_5m", "-1.5", "1"),
        ("gt_3_0m", "-3.0", "1"),
    ]

    # `gdal_calc.py` expression syntax assumes source band 1.
    for name, threshold, _ in classes:
        mask = out / f"{name}.tif"
        subprocess.run([
            "gdal_calc.py",
            "-A", depth_tif,
            "--calc", f"A>{threshold}",
            "--NoDataValue=0",
            "--type=Byte",
            "--outfile", str(mask),
            "--overwrite",
        ], check=True)

        shp_dir = out / name
        shp_dir.mkdir(exist_ok=True)
        subprocess.run([
            "gdal_polygonize.py",
            str(mask), "-f", "ESRI Shapefile",
            str(shp_dir / f"{name}.shp"),
            name, "DN",
        ], check=True)
```

## 14.3 Merge into one hazard SHP

Use OGR/GeoPandas to append a `hazard` code and `depth_min/depth_max` attributes. The Shapefile bundle must include `.shp/.shx/.dbf/.prj`; field-name length limits should be respected.

Recommended fields:

```text
hazard     CHAR(2)
dmin_m     REAL
dmax_m     REAL
area_m2    REAL
sim_id     TEXT
```

## 14.4 KML

Two products:

1. Vector `GroundOverlay` polygon hierarchy for flood classes.
2. Raster `GroundOverlay` for depth/arrival GeoTIFF rendered through a PNG tile/image.

Use GDAL/OGR for vector export and an explicit KML generation layer when nested folders/style/opacity are required.

Example KML scaffold:

```python
from xml.etree.ElementTree import Element, SubElement, tostring

KML_NS = "http://www.opengis.net/kml/2.2"


def polygon_style(parent, name, color):
    style = SubElement(parent, "{%s}Style" % KML_NS, id=name)
    poly = SubElement(style, "{%s}PolyStyle" % KML_NS)
    SubElement(poly, "{%s}color" % KML_NS).text = color
    return style
```

For a real export, use `ogr2ogr -f KML` for geometry and then inject style/folder metadata using lxml or OGR layer/style configuration.

---

# 15. Frontend Implementation Blueprint

## 15.1 Map architecture

```text
MapLibre GL
  ├─ satellite/basemap raster
  ├─ 3D terrain
  ├─ vector boundaries
  └─ deck.gl overlays
       ├─ flood raster tiles
       ├─ road/building layers
       ├─ flow arrows
       └─ observation masks
```

## 15.2 React component

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { BitmapLayer } from "@deck.gl/layers";

export default function FloodMap({
  floodUrls,
  satelliteUrl,
}: {
  floodUrls: string[];
  satelliteUrl?: string;
}) {
  const mapRef = useRef<maplibregl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [step, setStep] = useState(0);
  const [compare, setCompare] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [78.1, 30.1],
      zoom: 11,
      pitch: 50,
    });

    map.on("load", () => {
      map.addSource("terrain", {
        type: "raster-dem",
        tiles: ["https://your-tile-service/terrain/{z}/{x}/{y}.png"],
        tileSize: 256,
        maxzoom: 14,
      });
      map.setTerrain({ source: "terrain", exaggeration: 1.4 });

      const overlay = new MapboxOverlay({
        interleaved: true,
        layers: [],
      });
      map.addControl(overlay as any);
      overlayRef.current = overlay;
    });

    mapRef.current = map;
    return () => map.remove();
  }, []);

  useEffect(() => {
    if (!overlayRef.current || !floodUrls.length) return;
    const layer = new BitmapLayer({
      id: "flood-depth",
      image: floodUrls[Math.min(step, floodUrls.length - 1)],
      bounds: [78.0, 29.9, 78.4, 30.3],
      opacity: 0.75,
    });

    overlayRef.current.setProps({ layers: [layer] });
  }, [floodUrls, step]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute bottom-4 left-4 right-4 rounded bg-white/90 p-3 shadow">
        <div className="flex items-center gap-3">
          <button onClick={() => setStep(0)}>0</button>
          <input
            className="flex-1"
            type="range"
            min={0}
            max={Math.max(0, floodUrls.length - 1)}
            value={step}
            onChange={(e) => setStep(Number(e.target.value))}
          />
          <span>{step}</span>
          <button onClick={() => setCompare(v => !v)}>
            {compare ? "Satellite on" : "Satellite off"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

For a production application, raster animation should use **tiled COG/WMTS/XYZ tiles** rather than sending full GeoTIFFs to the browser. The supplied product report similarly emphasizes tiles/streaming/server-side processing for large rasters. fileciteturn0file0L2375-L2386

## 15.3 Time-slider storage strategy

Option A — pre-generated XYZ/COG tiles per output timestep:

```text
flood/{sim_id}/depth/t0000/{z}/{x}/{y}.png
flood/{sim_id}/depth/t0060/{z}/{x}/{y}.png
...
```

Option B — a dynamic tile service reading a multiband/NetCDF/Zarr dataset.

Recommended for hackathon: pre-generate tiles for the selected simulation after completion.

---

# 16. Web UI Layout

## 16.1 Scenario builder

```text
+------------------------------------------------------------+
| PROJECT / DAM / RIVER                                     |
+----------------------+-------------------------------------+
| Scenario Inputs      | Interactive map                    |
| Reservoir level      |                                     |
| Inflow/Q             | DEM + satellite                    |
| Breach model         | Dam                                |
| Breach width        | River                              |
| Formation time       | Domain boundary                   |
| Manning source       |                                     |
| Solver: [x] D-Flow  |                                     |
|         [x] SPH      |                                     |
|                       |                                     |
| [Validate] [Run]    |                                     |
+----------------------+-------------------------------------+
```

## 16.2 Result view

```text
+------------------------------------------------------------------------+
| Simulation #1827   COMPLETED           Solver: D-Flow FM               |
+-----------------------------------------------------------------------+
| Peak Area | Max Depth | Max Velocity | Arrival | Assets               |
| 42.5 km2  | 8.2 m     | 5.1 m/s      | 31 min  | 8 villages          |
+------------+-----------------------------------------------------------+
| Layers     |                     MAP                                   |
| [x] depth |                                                             |
| [ ] vel   |                  flood propagation                       |
| [x] arr   |                                                             |
| [x] sat   |                                                             |
+------------+-----------------------------------------------------------+
| 00:00 ----- 00:10 ----- 00:20 ----- 00:30 ----- 01:00 ------->       |
+------------------------------------------------------------------------+
```

The supplied report identifies time-dependent flood animation and comparison view as high-value features. fileciteturn0file0L1345-L1386

---

# 17. AI / Machine Learning Layer

# 17.1 Physics-informed surrogate architecture

The surrogate should not be marketed as a universal replacement for the hydraulic solver. It is a reduced-order model trained only over a documented parameter/domain envelope.

## Candidate architecture A — U-Net

Input tensor channels:

```text
DEM
Manning n
Initial depth
River mask
Breach mask
Reservoir level
```

Global scalar inputs:

```text
Q0
breach width
formation time
simulation horizon
```

Output tensor:

```text
depth(x,y)
velocity(x,y)
arrival(x,y)
```

Loss:

\[
L = \lambda_1L_{depth}+\lambda_2L_{velocity}+\lambda_3L_{arrival}+\lambda_4L_{physics}
\]

Possible physics regularizers:

\[
L_{mass}=\left|\Delta V-\int(Q_{in}-Q_{out})dt\right|
\]

\[
L_{nonnegative}=\mathbb{E}[\max(0,-h)]
\]

## Candidate architecture B — Fourier Neural Operator

Use when the dataset consists of many simulations over the same or closely aligned spatial domain.

Operator view:

\[
\mathcal{G}: (\text{terrain},\text{forcing},\text{scenario})
\rightarrow h(x,y,t)
\]

FNO is attractive when the aim is rapid field inference across parameterized PDE families, but it requires a large, diverse training set.

## Inference gate

The service should return:

```json
{
  "mode": "surrogate",
  "confidence": 0.87,
  "domain_of_validity": {
    "breach_width_m": [50, 150],
    "reservoir_level_m": [790, 825]
  },
  "requires_physics_fallback": false
}
```

If any input falls outside the training envelope, automatically route to a full physics simulation.

---

# 17.2 Automated calibration with Optuna

Objective:

\[
J(\theta)=
\alpha(1-IoU)
+\beta|A_p-A_o|/A_o
+\gamma FNR
+\delta FPR
\]

where \(\theta\) can include:

```text
Manning n multiplier
breach width multiplier
formation time multiplier
initial water level offset
boundary discharge multiplier
```

Optuna loop:

```python
import optuna


def objective(trial):
    n = trial.suggest_float("manning_n", 0.025, 0.12)
    breach_w = trial.suggest_float("breach_width_m", 50.0, 180.0)
    tf = trial.suggest_float("formation_time_s", 60.0, 600.0, log=True)

    sim_id = run_dflowfm_with_params(
        manning_n=n,
        breach_width_m=breach_w,
        formation_time_s=tf,
    )
    pred = load_flood_mask(sim_id)
    obs = load_observed_mask()
    m = binary_metrics(pred, obs)
    return (
        1.0 - m["iou"]
        + 0.25 * m["fpr"]
        + 0.25 * m["fnr"]
    )


study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=30)
print(study.best_params)
```

**Safety gate:** calibration must not silently change the scenario beyond documented bounds. Every trial is stored with parameters and metrics.

---

# 18. AI Result Interpretation Layer

The LLM layer should operate only over structured outputs.

Bad architecture:

```text
simulation image -> LLM guesses risk
```

Correct architecture:

```text
Simulation DB / PostGIS / summary.json
              |
          structured query
              |
            LLM
              |
      grounded explanation
```

Example tool query:

```json
{
  "query_type": "assets_arriving_before",
  "simulation_id": "sim_123",
  "minutes": 30,
  "asset_types": ["village", "hospital", "bridge"]
}
```

The result returned to the language model is:

```json
{
  "villages": 6,
  "hospitals": 1,
  "bridges": 2,
  "records": [
    {"name":"Village A","arrival_min":21.5}
  ]
}
```

The LLM is then used as an explanation interface, not as the numerical source of truth.

---

# 19. Indian Demonstration Case Studies

# 19.1 Case A — Rishi Ganga / Dhauliganga mountainous flash flood

## Objective

Demonstrate:

- steep terrain;
- narrow gorge routing;
- sudden upstream water release;
- near-field high-energy flow;
- satellite validation.

## Suggested domain

```text
Dam/blockage location
      |
      +-- 1–5 km upstream
      +-- 20–50 km downstream corridor
```

The exact domain must be determined from the chosen event geometry and available DEM/hydrology; do not hard-code an assumed breach location from memory.

## Terrain

Preferred:

- Copernicus DEM GLO-30.
- Higher-resolution authoritative terrain if available.

## River geometry

- HydroRIVERS for initial river trace.
- OpenStreetMap/local hydrography for visualization.
- Derive local centerline/bank geometry from high-resolution imagery where practical.

## Hydrology

Use Indian gauge/discharge archives where accessible; where a historical event hydrograph is incomplete, define the demonstration as a **scenario reconstruction** rather than claiming measured truth.

## Satellite validation

Sentinel-1 GRD before/during/after the event through GEE.

## SPH focus

Use a localized near-field subdomain around the breach/flow constriction.

## D-Flow FM focus

Use the wider downstream routing/floodplain where the flow exits the gorge.

---

# 19.2 Case B — Kosi 2008 or Machchhu-II alluvial floodplain

A second demonstration should be geomorphologically different from the mountain case.

## Preferred characteristics

- flatter terrain;
- broad floodplain;
- large lateral inundation area;
- more exposure assets;
- longer travel time;
- clear impact-analysis story.

## Kosi option

Use an event-reconstruction domain centered on the 2008 breach area with:

- Copernicus DEM GLO-30;
- HydroRIVERS-derived river network;
- historical/event-specific geometry from open/public records where legally reusable;
- OSM exposure assets;
- Sentinel-1 event-window observations.

## Machchhu-II option

Use a generalized dam-breach scenario around a real dam geometry and simulate several breach-width/formation-time alternatives. This is particularly suitable if historical high-quality observation data are easier to validate.

## Demo storytelling contrast

```text
CASE A: mountain
high slope -> high velocity -> narrow corridor

CASE B: alluvial
low slope -> wide spreading -> larger exposed area
```

This contrast demonstrates why one generalized solver workflow must support different terrain regimes.

---

# 20. Open Data Acquisition Matrix

| Dataset | Purpose | Recommended acquisition |
|---|---|---|
| Copernicus DEM GLO-30 | terrain | Copernicus Data Space/OData/S3 |
| Copernicus DEM GLO-90 | screening/fallback | Copernicus Data Space |
| HydroRIVERS | river network prior | HydroSHEDS / FAO-derived catalogue |
| OSM | exposure | Overpass API |
| Sentinel-1 GRD | observed flood | Google Earth Engine |
| Sentinel-2 | optical context | Google Earth Engine |
| India-WRIS | hydrology/reference | India-WRIS portal/available archives |

Copernicus currently documents GLO-30 global coverage and downloadable/API access subject to the current access category. citeturn536822search3turn536822search5

HydroRIVERS is based on HydroSHEDS and provides generalized global river lines. citeturn953931search9

Overpass is a read-only query system designed for selective OSM extraction. citeturn536822search9

---

# 21. Exposure Data Pipeline

## 21.1 Overpass query examples

### Buildings

```text
[out:json][timeout:60];
(
  way[building](29.9,78.0,30.3,78.4);
  relation[building](29.9,78.0,30.3,78.4);
);
out geom;
```

### Hospitals/schools

```text
[out:json][timeout:60];
(
  nwr[amenity=hospital](29.9,78.0,30.3,78.4);
  nwr[amenity=school](29.9,78.0,30.3,78.4);
);
out center geom;
```

### Bridges

```text
[out:json][timeout:60];
nwr[man_made=bridge](29.9,78.0,30.3,78.4);
out geom;
```

Always cache the downloaded raw response and record retrieval time because OSM is mutable.

---

# 22. Export/Visualization Tile Architecture

## 22.1 Raster path

```text
NetCDF/VTK
  -> GDAL/rasterio
  -> COG GeoTIFF
  -> overviews
  -> tile generation
  -> object storage
  -> browser tiles
```

Recommended raster products:

```text
max_depth.tif       FLOAT32
max_velocity.tif    FLOAT32
arrival_time.tif    FLOAT32
flood_extent.tif    BYTE
hazard_class.tif    BYTE
```

## 22.2 Vector path

```text
flood mask
 -> polygonize
 -> simplify (topology-aware)
 -> MultiPolygon
 -> GeoJSON / MVT
 -> PostGIS/object store
```

Do not simplify the raw scientific polygon irreversibly. Keep:

```text
scientific_raw.geojson
web_simplified.geojson
web_tiles.pmtiles
```

---

# 23. Performance and Scaling

## 23.1 Resolution tiers

| Tier | Resolution | Purpose |
|---|---:|---|
| R1 | 30 m | rapid screening |
| R2 | 10 m | detailed catchment model |
| R3 | 1–5 m | localized high-detail/structure domain |

These are product modes, not fixed physical requirements, consistent with the supplied report's warning that resolution should depend on data and compute. fileciteturn0file0L2019-L2044

## 23.2 Chunking

NetCDF/xarray:

```python
ds = xr.open_dataset(path, chunks={"time": 1, "y": 1024, "x": 1024})
```

For very large simulations, move to Zarr for normalized analytics while preserving original NetCDF artifacts.

## 23.3 Object naming

```text
s3://flood-platform/
  projects/{project_id}/
    datasets/{dataset_id}/raw/*
    datasets/{dataset_id}/processed/*
    scenarios/{scenario_id}/scenario.json
    simulations/{simulation_id}/input/*
    simulations/{simulation_id}/raw/*
    simulations/{simulation_id}/products/*
    simulations/{simulation_id}/exports/*
    simulations/{simulation_id}/logs/*
```

---

# 24. Production Docker Compose

Docker Compose supports GPU reservations through `deploy.resources.reservations.devices`; NVIDIA Compose documentation likewise shows `driver: nvidia`, GPU capabilities and GPU count/device IDs. citeturn860744search1turn860744search0

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - api

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://flood:flood@postgis:5432/flood
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      S3_BUCKET: flood
    depends_on:
      - postgis
      - redis
      - minio

  worker-cpu:
    build:
      context: ./backend
      dockerfile: Dockerfile.cpu-worker
    command: celery -A app.celery worker -Q cpu --loglevel=INFO
    environment:
      DATABASE_URL: postgresql+psycopg://flood:flood@postgis:5432/flood
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
    depends_on:
      - postgis
      - redis
      - minio

  worker-gpu:
    build:
      context: ./simulation
      dockerfile: Dockerfile.dualsphysics
    command: celery -A worker.celery worker -Q gpu --loglevel=INFO --concurrency=1
    environment:
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - redis
      - minio

  gis-worker:
    build: ./gis
    command: celery -A worker.celery worker -Q gis --loglevel=INFO --concurrency=2
    environment:
      REDIS_URL: redis://redis:6379/0
      S3_ENDPOINT: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
    depends_on:
      - redis
      - minio

  postgis:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: flood
      POSTGRES_USER: flood
      POSTGRES_PASSWORD: flood
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  miniodata:
```

## 24.1 Production changes

Do not deploy the demo credentials above into production. Replace with:

- Docker secrets/Vault;
- TLS;
- non-public Postgres/Redis/MinIO endpoints;
- separate internal network;
- object-store IAM users with least privilege;
- resource limits;
- worker queues segregated by solver.

---

# 25. Container Images

## 25.1 FastAPI/GIS CPU image

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev proj-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 25.2 GPU worker

Use an NVIDIA CUDA base image compatible with the pinned DualSPHysics build and host driver. Do not choose a random CUDA version merely because a newer image exists.

Example structure:

```dockerfile
FROM nvidia/cuda:12.9.0-runtime-ubuntu22.04
WORKDIR /opt/flood
COPY dualsphysics/ /opt/dualsphysics/
COPY worker/ /opt/flood/worker/
RUN apt-get update && apt-get install -y python3 python3-pip
RUN pip3 install celery redis boto3
ENV PATH="/opt/dualsphysics/bin:${PATH}"
CMD ["celery", "-A", "worker.celery", "worker", "-Q", "gpu", "--concurrency=1"]
```

The exact CUDA runtime must match the pinned binary build.

---

# 26. Simulation Job State Machine

```text
DRAFT
  |
  v
VALIDATING
  |
  +----> INVALID
  |
  v
QUEUED
  |
  v
PREPARING
  |
  v
MESHING
  |
  v
RUNNING
  |
  +----> FAILED
  |
  v
PARSING
  |
  v
POSTPROCESSING
  |
  v
IMPACT_ANALYSIS
  |
  v
VALIDATING_OUTPUT
  |
  v
COMPLETED
```

Each state emits:

```json
{
  "simulation_id": "...",
  "state": "POSTPROCESSING",
  "progress_pct": 82.4,
  "message": "Writing COG max_depth.tif",
  "timestamp": "..."
}
```

---

# 27. Progress Estimation

Simulation progress should not be fake percentage increments. Use phase-weighted progress.

Example:

```text
Input validation      5%
Dataset preparation  15%
Grid/mesh generation 10%
Solver execution     50%
Result parsing        8%
GIS/postprocess       7%
Validation             5%
```

For solver runtime, use:

- elapsed/estimated duration if the engine reports it;
- timestep count / expected timestep count if available;
- output file timestamps;
- log pattern matching.

Otherwise expose:

```text
RUNNING — elapsed 13m 42s
```

rather than a fabricated `73%`.

---

# 28. Validation and QA Gate

A simulation is not `COMPLETED` merely because the solver process exits with code 0.

## Automated checks

### Input

- CRS defined.
- DEM has no unexpected nodata inside domain.
- Units validated.
- Reservoir level above dam/breach geometry where physically intended.
- Breach dimensions positive.
- Domain contains downstream boundary.

### Numerical

- solver exit code zero;
- output files present;
- finite values;
- no impossible NaN/Inf explosion;
- dry-area fraction within expected range;
- mass/conservation error below configurable tolerance.

### Product

- max depth raster exists;
- flood extent polygon non-empty when event should inundate;
- CRS metadata present;
- pixel alignment consistent;
- result manifest created.

### Validation

- GEE observation available;
- same CRS/grid;
- metrics generated;
- uncertainty notes attached.

---

# 29. Reproducibility Contract

Every simulation stores:

```text
scenario.json
input manifest
input checksums
solver version
container image digest
DEM checksum
roughness checksum
forcing checksum
Git commit
random seeds
CPU/GPU info
command line
stdout/stderr
raw outputs
normalized outputs
validation metrics
```

The supplied report explicitly says each simulation should retain input data, scenario parameters, software versions, model settings, seeds where applicable, outputs and validation metrics. fileciteturn0file0L2347-L2359

## Scenario hash

```python
import hashlib
import json


def scenario_hash(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()
```

This allows duplicate scenario detection.

---

# 30. API Surface

## Core

```text
POST   /api/v1/projects
GET    /api/v1/projects/{id}
POST   /api/v1/datasets/ingest
POST   /api/v1/scenarios
GET    /api/v1/scenarios/{id}
POST   /api/v1/simulations/run
GET    /api/v1/simulations/{id}/status
GET    /api/v1/simulations/{id}/events
GET    /api/v1/simulations/{id}/results
GET    /api/v1/simulations/{id}/exports
POST   /api/v1/simulations/{id}/validate
```

## Satellite

```text
POST /api/v1/earth-observation/flood-detection
GET  /api/v1/earth-observation/{id}
POST /api/v1/earth-observation/{id}/compare/{simulation_id}
```

## AI

```text
POST /api/v1/ai/recommend-parameters
POST /api/v1/ai/calibrate
POST /api/v1/ai/surrogate/infer
POST /api/v1/ai/explain
```

---

# 31. Security Model

## Authentication

Use OIDC/OAuth2 via a standard identity provider.

## Roles

```text
viewer
analyst
modeler
admin
```

## Simulation isolation

Never execute user-supplied shell commands directly.

Use:

```text
validated parameter schema
allowlisted executables
read-only base images
resource limits
working-directory isolation
no host filesystem mount except designated data volumes
```

## Object storage

Each job gets a random prefix and short-lived signed URLs for browser access.

## Audit log

Capture:

```text
who
what
when
scenario_id
old_value
new_value
result
```

---

# 32. Failure Handling

## Failure class table

| Failure | Action |
|---|---|
| DEM missing | block run |
| invalid CRS | auto-fix if unambiguous, otherwise block |
| GEE unavailable | mark validation unavailable; physics run may continue |
| solver crash | retry once for transient infra errors; preserve logs |
| GPU unavailable | queue or switch to CPU only if explicitly supported |
| result file missing | fail QA |
| empty flood mask | warn or fail depending on expected scenario |
| excessive mass error | fail QA / flag model instability |

Never automatically retry a physically invalid model input indefinitely.

---

# 33. Recommended Repository Structure

```text
flood-platform/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── map/
│   └── lib/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── datasets/
│   │   │   ├── dflowfm/
│   │   │   ├── dualsphysics/
│   │   │   ├── gis/
│   │   │   ├── satellite/
│   │   │   └── ai/
│   │   ├── tasks/
│   │   └── main.py
│   └── tests/
├── simulation/
│   ├── dflowfm/
│   ├── dualsphysics/
│   └── templates/
├── gis/
│   ├── Dockerfile
│   └── worker/
├── infra/
│   ├── docker-compose.yml
│   ├── postgres/
│   └── minio/
├── datasets/
├── notebooks/
├── docs/
└── scripts/
```

This structure extends the supplied product report's proposed repository organization. fileciteturn0file0L1732-L1760

---

# 34. Testing Strategy

## Unit tests

- breach formula outputs;
- scenario validation;
- CRS transformations;
- mask metrics;
- export thresholds;
- schema validation.

## Golden tests

Maintain a small deterministic benchmark case:

```text
dam-break rectangular channel
known analytical/reference behavior
```

Compare:

- peak discharge;
- wave-front arrival;
- maximum depth;
- water volume.

## Integration tests

```text
POST scenario
 -> queue task
 -> generate case
 -> mocked solver
 -> parse artifact
 -> publish product
```

## System test

One full real-data Indian case with pinned inputs and expected metric ranges.

---

# 35. Observability

## Logs

Structured JSON logs:

```json
{
  "timestamp": "...",
  "service": "worker-gpu",
  "simulation_id": "sim_123",
  "phase": "solver",
  "message": "PartVTK complete",
  "duration_s": 42.7
}
```

## Metrics

Prometheus-compatible:

```text
simulation_jobs_total
simulation_failures_total
simulation_runtime_seconds
simulation_queue_latency_seconds
gis_processing_seconds
gee_requests_total
gee_failures_total
gpu_utilization_percent
memory_peak_bytes
```

---

# 36. Cost/Compute Model

The expensive operations are:

```text
1. high-resolution SPH particle count
2. high-resolution D-Flow FM timesteps
3. repeated calibration runs
4. large raster/vector transformations
5. AI surrogate training
```

Therefore the architecture supports:

```text
screening mode
    -> low resolution + fast D-Flow

detailed mode
    -> fine D-Flow

near-field research
    -> SPH GPU

uncertainty mode
    -> ensemble batch jobs

emergency mode
    -> surrogate, then confirm with physics
```

---

# 37. HADR Decision Products

The platform should convert solver outputs into decision-oriented products.

## 37.1 Evacuation arrival map

```text
0–15 min
15–30 min
30–60 min
60–120 min
>120 min
```

## 37.2 Hazard matrix

Example configurable classification based on depth and velocity:

```text
H = depth class
V = velocity class
Risk = lookup(H, V)
```

Do not claim a universal life-safety threshold. Keep thresholds explicitly versioned and sourced.

## 37.3 Asset prioritization

```sql
SELECT asset_type, name, arrival_min, max_depth_m, max_velocity_ms
FROM asset_hazard_view
WHERE arrival_min <= 60
ORDER BY arrival_min ASC, max_depth_m DESC;
```

---

# 38. Scenario Ensemble Engine

A single simulation is often not enough because breach width, formation time and roughness are uncertain.

## Ensemble definition

```json
{
  "base_scenario": "scenario_001",
  "parameters": {
    "breach_width_m": [60, 90, 120, 150],
    "formation_time_s": [60, 120, 240, 480],
    "manning_multiplier": [0.8, 1.0, 1.2]
  },
  "strategy": "latin_hypercube",
  "n": 50
}
```

The orchestration layer expands this into independent Celery jobs.

## Ensemble products

```text
P10 flood extent
P50 flood extent
P90 flood extent
probability of inundation
probability of arrival < T
```

This is more decision-relevant than presenting a single deterministic line.

---

# 39. Domain Adaptation Between Mountain and Alluvial Cases

The platform should expose regime indicators:

```text
mean slope
max slope
channel width
relief
terrain roughness
floodplain width
river sinuosity
```

Then choose defaults:

```python
if mean_slope > 0.03 and floodplain_width_km < 2:
    profile = "mountain"
elif mean_slope < 0.005 and floodplain_width_km > 5:
    profile = "alluvial"
else:
    profile = "mixed"
```

These are **heuristic product profiles**, not hydraulic laws.

---

# 40. Satellite/Simulation Comparison UI

## Difference classes

```text
SIMULATED + OBSERVED -> agreement
SIMULATED only       -> overprediction
OBSERVED only        -> underprediction
```

The map should display:

```text
Agreement      opacity 0.70
Overprediction opacity 0.55
Underprediction opacity 0.55
```

The metric drawer shows:

```text
IoU / CSI
FPR
FNR
Observed area
Simulated area
Intersection area
Boundary mean distance
```

---

# 41. GEE Export Strategy

The backend should not request pixel-by-pixel data from Earth Engine for every map interaction.

Preferred flow:

```text
GEE server computation
       |
       +--> Export image to cloud object/asset
       |
       +--> Export vector mask if small enough
       v
local object store
       |
       v
COG / GeoJSON / tiles
```

Google documents Earth Engine Python initialization and service-account patterns for applications. citeturn596341search0turn596341search1

---

# 42. Technical Corrections to the Preliminary Product Report

This section intentionally distinguishes additions/corrections from the supplied preliminary architecture.

## 42.1 D-Flow FM boundary-file naming

The preliminary report requests `.bnd` and `.ext`. Modern D-Flow FM documentation uses `.ext` for external forcing and commonly references `.bc` forcing and `.pli` boundary support geometry. Legacy `.bnd/.bct` naming exists in older/conversion contexts. The implementation must pin a D-Flow FM release and generate files according to that release's schema. citeturn418439search0turn418439search17

## 42.2 Sentinel-1 corrections

The preliminary requirement mentions border-noise removal and thermal-noise correction as application steps. For `COPERNICUS/S1_GRD`, Earth Engine already performs those during ingestion. The application should document them as **upstream GEE preprocessing guarantees** and then perform only application-level filtering/change detection. citeturn953931search2

## 42.3 “Near-real-time” meaning

GEE can process newly available imagery quickly, but end-to-end latency depends on Sentinel-1 acquisition, ingestion, orbit processing, user access and export. The platform should report actual observation time and processing time rather than claiming a fixed latency.

## 42.4 Copernicus 30 m access

As of the current 2026 Copernicus Data Space documentation, COP-DEM GLO-30 programmatic access is subject to the current CCM authorization category. The deployment should therefore support SRTM/Copernicus-90 fallback and should fail clearly when the required 30 m access credential is absent. citeturn536822search1turn536822search3

---

# 43. What to Build First

The supplied report's engineering priority is the correct overall order: prove physics, automate it, normalize outputs, build GIS, then add SPH, satellite and AI. fileciteturn0file0L2546-L2569

## Stage 1 — Physics proof

```text
one dam
one river
one DEM
one breach law
D-Flow FM
max-depth + extent
```

## Stage 2 — Product data contract

```text
PostGIS
MinIO
Scenario JSON
Result manifest
```

## Stage 3 — Web GIS

```text
MapLibre
scenario builder
job status
time slider
```

## Stage 4 — SPH

```text
near-field domain
DualSPHysics GPU
same scenario inputs
comparison dashboard
```

## Stage 5 — Satellite validation

```text
Sentinel-1
GEE mask
IoU/CSI/FPR/FNR
```

## Stage 6 — AI

```text
calibration
surrogate
result interpretation
```

---

# 44. Recommended Final Demonstration Sequence

The supplied report proposes a demonstration from dam selection through GIS validation/export. The implementation-ready version is:

```text
01  Open project
02  Select dam/river
03  Show satellite + DEM context
04  Load data-quality panel
05  Configure breach
06  Show auto-derived breach parameters
07  Validate scenario
08  Submit D-Flow FM
09  Show live job phase/progress
10  Display flood propagation
11  Switch depth / velocity / arrival
12  Overlay villages / roads / buildings
13  Launch/inspect SPH near-field comparison
14  Open GEE observed-flood layer
15  Compute IoU / CSI / FPR / FNR
16  Show parameter calibration result
17  Export SHP
18  Export KML
19  Save reproducible scenario
```

This demonstrates essentially every required component while keeping the physics engine and observation pipeline visibly separate.

---

# 45. Technical Definition of the Final Product

> **A reproducible, GIS-native dam-break decision-support platform that ingests terrain, hydrograph, river, dam, land-cover and Earth-observation datasets; automatically constructs scenario inputs; executes D-Flow FM and DualSPHysics through isolated compute workers; converts time-dependent solver outputs into standardized depth, velocity, arrival-time, duration and flood-extent products; performs PostGIS exposure analysis; validates flood extent against Sentinel-1 observations processed in Google Earth Engine; and uses optimization/ML as an acceleration and calibration layer around the underlying physics.**

This extends the supplied one-sentence definition while preserving its central architecture: physics engine + GIS engine + satellite observation + AI + web decision-support interface. fileciteturn0file0L2581-L2635

---

# 46. Implementation Checklist

## Platform

- [ ] PostGIS 16 deployed.
- [ ] MinIO deployed.
- [ ] Redis deployed.
- [ ] FastAPI deployed.
- [ ] Celery CPU/GPU queues separated.
- [ ] Next.js map application deployed.

## Physics

- [ ] D-Flow FM version pinned.
- [ ] D-Flow FM model template validated against target version.
- [ ] Grid generation tested.
- [ ] Boundary generation tested.
- [ ] NetCDF parser tested against real outputs.
- [ ] DualSPHysics version pinned.
- [ ] GenCase template validated.
- [ ] GPU execution validated.
- [ ] PartVTK/IsoSurface pipeline validated.

## Geospatial

- [ ] DEM ingestion.
- [ ] CRS/vertical metadata.
- [ ] Roughness raster.
- [ ] HydroRIVERS import.
- [ ] OSM Overpass importer.
- [ ] COG creation.
- [ ] polygonization.
- [ ] SHP/KML export.

## Satellite

- [ ] GEE project enabled.
- [ ] service account/ADC configured.
- [ ] Sentinel-1 query.
- [ ] baseline composite.
- [ ] optional refined Lee.
- [ ] log-ratio.
- [ ] Otsu threshold.
- [ ] morphology.
- [ ] export/cache.

## AI

- [ ] calibration objective.
- [ ] Optuna study storage.
- [ ] trial provenance.
- [ ] surrogate data generator.
- [ ] surrogate validation.
- [ ] out-of-domain detector.

## QA

- [ ] mass-balance threshold.
- [ ] golden dam-break case.
- [ ] solver comparison metrics.
- [ ] satellite comparison.
- [ ] reproducibility hash.
- [ ] audit logging.

---

# 47. Reference Sources / Technical Authorities

## User-supplied reference

- `Dam_Break_Flood_Simulation_AI_Product_Report(1).md` — preliminary product, simulation, GIS, satellite, AI and architecture report. fileciteturn0file0L1450-L1524

## Delft3D / D-Flow FM

- Deltares D-Flow FM technical reference/manuals: https://oss.deltares.nl/web/delft3dfm/downloads
- D-Flow FM external forcing / hydrolib-core: https://deltares.github.io/HYDROLIB-core/0.10.1/reference/models/ext/
- D-Flow FM 2D shallow-water equations: technical reference material and derivative literature. citeturn953931search0turn953931search1

## DualSPHysics / SPH

- DualSPHysics running examples and GPU execution: https://github.com/DualSPHysics/DualSPHysics/wiki/5.-Running-DualSPHysics
- DualSPHysics PartVTK command reference: https://github.com/DualSPHysics/DualSPHysics/blob/master/doc/help/PartVTK_Help.out
- Wendland/Tait/SPH equations: SPH technical literature and reference implementations. citeturn690351search0turn690351search2

## Dam breach

- USACE HEC-RAS breach parameter guidance: https://www.hec.usace.army.mil/confluence/rasdocs/ras1dtechref/6.1/performing-a-dam-break-study-with-hec-ras/estimating-dam-breach-parameters/estimating-breach-parameters
- Froehlich 2008: ASCE Journal of Hydraulic Engineering. citeturn250464search2
- MacDonald & Langridge-Monopolis 1984: ASCE Journal of Hydraulic Engineering. citeturn250464search4

## Earth observation

- Google Earth Engine Sentinel-1 algorithms: https://developers.google.com/earth-engine/guides/sentinel1
- Google Earth Engine Sentinel-1 change detection tutorial: https://developers.google.com/earth-engine/tutorials/community/detecting-changes-in-sentinel-1-imagery-pt-1
- Earth Engine authentication/service accounts: https://developers.google.com/earth-engine/guides/service_account

## Geospatial infrastructure

- PostGIS spatial indexes: https://postgis.net/docs/en/using_postgis_dbmanagement.html
- GDAL polygonization: https://gdal.org/en/stable/programs/gdal_polygonize.html
- xarray NetCDF loading: https://docs.xarray.dev/en/latest/generated/xarray.open_dataset.html
- Docker Compose GPU support: https://docs.docker.com/compose/how-tos/gpu-support/

## Indian / open data ecosystem

- Copernicus Data Space DEM documentation: https://documentation.dataspace.copernicus.eu/Data/Others/CCM.html
- HydroRIVERS/HydroSHEDS-derived river network information: FAO AQUASTAT catalogue. citeturn953931search9
- OpenStreetMap Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API

---

# Appendix A — Minimal Operational Commands

## Start platform

```bash
docker compose up -d --build
```

## Apply database schema

```bash
psql "$DATABASE_URL" -f infra/postgres/schema.sql
```

## Test GPU worker

```bash
docker compose run --rm worker-gpu nvidia-smi
```

## Submit a scenario

```bash
curl -X POST http://localhost:8000/api/v1/simulations/run \
  -H 'Content-Type: application/json' \
  -d '{
    "scenario_id": "00000000-0000-0000-0000-000000000001",
    "solvers": ["dflowfm", "dualsphysics"],
    "async_mode": true
  }'
```

## Inspect task queue

```bash
docker compose exec redis redis-cli keys 'simulation:*'
```

---

# Appendix B — Result Manifest Example

```json
{
  "schema_version": "1.0.0",
  "simulation_id": "sim-001",
  "solver": "dflowfm",
  "solver_version": "pinned",
  "domain": {
    "crs": "EPSG:32644",
    "width_px": 2048,
    "height_px": 1536,
    "resolution_m": 10
  },
  "time": {
    "start": "2026-09-06T00:00:00Z",
    "end": "2026-09-06T06:00:00Z",
    "interval_s": 60
  },
  "products": [
    {"name": "max_depth", "uri": "s3://.../max_depth.tif"},
    {"name": "max_velocity", "uri": "s3://.../max_velocity.tif"},
    {"name": "arrival_time", "uri": "s3://.../arrival_time.tif"},
    {"name": "flood_extent", "uri": "s3://.../flood_extent.geojson"}
  ],
  "qc": {
    "mass_balance_error": 0.012,
    "nan_fraction": 0.0,
    "valid": true
  }
}
```

---

# Appendix C — Recommended MVP Definition

The MVP should be:

```text
ONE DEM
ONE INDIAN DAM/RIVER
ONE D-FLOW FM CASE
ONE BREACH MODEL
ONE WEB MAP
ONE TIME SLIDER
ONE SATELLITE FLOOD MASK
ONE VALIDATION SCORECARD
ONE SHP EXPORT
ONE KML EXPORT
```

Then add:

```text
SPH near-field
ensemble uncertainty
Optuna calibration
surrogate AI
LLM result explanation
```

This preserves the fundamental rule from the supplied product report: **do not start with AI or a polished dashboard before proving that the physical pipeline produces a credible flood result.** fileciteturn0file0L2565-L2576

---

# Appendix D — Final Architecture Diagram

```text
                                  HUMAN / HADR
                                       |
                                       v
                     +-----------------------------------+
                     | Next.js + MapLibre + deck.gl      |
                     | Scenario | Monitor | Map | Report|
                     +------------------+----------------+
                                        |
                                 REST / WebSocket
                                        |
                                        v
                +-----------------------------------------------+
                | FastAPI                                       |
                | Auth | Project | Dataset | Scenario | Jobs    |
                +----------+------------------+-----------------+
                           |                  |
                           v                  v
                +----------------+      +-----------+
                | PostGIS 16     |      | Redis     |
                | metadata/GIS   |      | Celery    |
                +----------------+      +-----+-----+
                                              |
                    +-------------------------+----------------------+
                    |                         |                      |
                    v                         v                      v
             +-------------+          +-------------+        +-------------+
             | D-Flow FM   |          | SPH CUDA    |        | GIS/GEE     |
             | CPU worker  |          | GPU worker  |        | worker      |
             +------+------+          +------+------+        +------+------+
                    |                        |                      |
                    +------------+-----------+----------------------+
                                 |
                                 v
                         +---------------+
                         | Normalizer    |
                         | COG/GeoJSON   |
                         | metrics       |
                         +-------+-------+
                                 |
                 +---------------+----------------+
                 |                                |
                 v                                v
          +--------------+                 +---------------+
          | PostGIS      |                 | AI / Optuna   |
          | impacts      |                 | surrogate     |
          +--------------+                 +-------+-------+
                 \                                 /
                  \                               /
                   +-------------+---------------+
                                 |
                                 v
                          DECISION SUPPORT
                                 |
                     +-----------+-----------+
                     | Flood map             |
                     | Depth                  |
                     | Velocity               |
                     | Arrival time           |
                     | Exposure               |
                     | Satellite comparison   |
                     | SHP / KML              |
                     +------------------------+
```

---

**End of report.**
