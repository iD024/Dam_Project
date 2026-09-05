from backend.schemas.scenario_contract import ScenarioContract
from backend.schemas.api_schemas import AIInputCheckResponse, CheckItem

def check_scenario_input_quality(scenario: ScenarioContract) -> AIInputCheckResponse:
    checklist = []
    recommendations = []
    score_points = 0
    total_points = 6

    # 1. Terrain Check
    if scenario.terrain.dem_uri:
        checklist.append(CheckItem(
            item="Digital Elevation Model (DEM)",
            status="READY",
            details=f"DEM reference configured ({scenario.terrain.dem_uri}) at {scenario.terrain.resolution_m}m resolution",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Digital Elevation Model (DEM)",
            status="MISSING",
            details="No DEM URI specified for domain bathymetry",
        ))
        recommendations.append("Assign a Copernicus GLO-30 or SRTM GeoTIFF DEM layer.")

    # 2. Domain & CRS Check
    bbox = scenario.domain.bbox
    if len(bbox) == 4 and bbox[0] < bbox[2] and bbox[1] < bbox[3]:
        checklist.append(CheckItem(
            item="Domain Bounding Box & CRS",
            status="READY",
            details=f"Valid bounding box [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}] with CRS {scenario.domain.crs}",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Domain Bounding Box & CRS",
            status="INVALID",
            details="Bounding box coordinates are invalid or inverted",
        ))
        recommendations.append("Ensure bounding box coordinates follow [xmin, ymin, xmax, ymax] order.")

    # 3. Hydrology Check
    if scenario.hydrology.initial_reservoir_level_m > scenario.breach.bottom_elevation_m:
        head = scenario.hydrology.initial_reservoir_level_m - scenario.breach.bottom_elevation_m
        checklist.append(CheckItem(
            item="Hydraulic Head & Reservoir Storage",
            status="READY",
            details=f"Initial head is {head:.1f}m with active storage of {scenario.hydrology.initial_storage_m3/1e6:.1f}M m³",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Hydraulic Head & Reservoir Storage",
            status="INVALID",
            details=f"Reservoir level ({scenario.hydrology.initial_reservoir_level_m}m) is below breach invert ({scenario.breach.bottom_elevation_m}m)",
        ))
        recommendations.append("Ensure reservoir water elevation is strictly higher than breach bottom elevation.")

    # 4. Breach Parameters Check
    b_w = scenario.breach.bottom_width_m
    t_w = scenario.breach.top_width_m
    t_f = scenario.breach.formation_time_s
    if b_w > 0 and t_w >= b_w and t_f > 0:
        checklist.append(CheckItem(
            item="Breach Geometry & Failure Dynamics",
            status="READY",
            details=f"Trapezoidal breach (bottom {b_w}m, top {t_w}m) forming over {t_f}s",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Breach Geometry & Failure Dynamics",
            status="WARNING",
            details="Breach dimensions or formation time may be inconsistent",
        ))
        recommendations.append("Use AI Parameter Assistant to calculate Froehlich empirical breach parameters.")

    # 5. Roughness Check
    n_val = scenario.roughness.default_manning_n
    if 0.015 <= n_val <= 0.150:
        checklist.append(CheckItem(
            item="Surface Roughness (Manning's n)",
            status="READY",
            details=f"Manning coefficient n = {n_val:.3f} within standard hydraulic bounds",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Surface Roughness (Manning's n)",
            status="WARNING",
            details=f"Manning's n = {n_val:.3f} is outside typical channel/floodplain range (0.025 - 0.120)",
        ))
        recommendations.append("Verify whether extreme roughness is intentional.")

    # 6. Numerics & CFL Stability
    cfl = scenario.numerics.max_courant
    if cfl <= 1.0:
        checklist.append(CheckItem(
            item="Numerical Stability & CFL Constraint",
            status="READY",
            details=f"CFL Courant limit set to {cfl:.2f} (subcritical stability guaranteed)",
        ))
        score_points += 1
    else:
        checklist.append(CheckItem(
            item="Numerical Stability & CFL Constraint",
            status="WARNING",
            details=f"CFL Courant limit ({cfl:.2f}) > 1.0; risk of numerical dispersion or oscillations",
        ))
        recommendations.append("Set maximum Courant number <= 0.90 for explicit finite-volume solvers.")

    score_pct = (score_points / total_points) * 100.0
    if score_pct >= 90.0:
        overall = "READY"
    elif score_pct >= 60.0:
        overall = "WARNING"
    else:
        overall = "ACTION_REQUIRED"

    return AIInputCheckResponse(
        overall_status=overall,
        score_pct=score_pct,
        checklist=checklist,
        recommendations=recommendations,
    )
