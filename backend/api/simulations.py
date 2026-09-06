import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from backend.database import get_db
from backend.config import settings
from backend.models import Scenario, Simulation, SimulationResult, ExposureAsset
from backend.schemas.api_schemas import (
    SimulationRunRequest,
    SimulationResponse,
    SimulationStatusResponse,
    ImpactResponse,
)
from backend.schemas.scenario_contract import ScenarioContract
from backend.simulation_engines import get_simulation_engine
from backend.services.impact_service import compute_spatial_impacts

router = APIRouter(prefix="/simulations", tags=["Simulations"])

def execute_simulation_job(sim_id: str, db_factory, parameter_overrides: Optional[Dict[str, Any]] = None):
    """
    Background worker job that prepares, runs the hydrodynamic engine,
    normalizes the output, and performs PostGIS spatial impact analysis.
    """
    db: Session = db_factory()
    try:
        sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
        if not sim:
            return

        sim.status = "running"
        sim.started_at = datetime.now(timezone.utc)
        sim.current_phase = "Initializing model & bathymetry"
        sim.progress_pct = 5.0
        db.commit()

        scenario_orm = sim.scenario
        raw_config = dict(scenario_orm.engine_config) if isinstance(scenario_orm.engine_config, dict) else scenario_orm.engine_config.copy()
        
        # Apply physics parameter overrides from Scenario Builder if provided
        if parameter_overrides:
            import copy
            raw_config = copy.deepcopy(raw_config)
            if "breach" in raw_config and isinstance(raw_config["breach"], dict):
                bw = parameter_overrides.get("bottom_width_m", parameter_overrides.get("breachWidth"))
                if bw is not None:
                    raw_config["breach"]["bottom_width_m"] = float(bw)
                tw = parameter_overrides.get("top_width_m", parameter_overrides.get("topWidth"))
                if tw is not None:
                    raw_config["breach"]["top_width_m"] = float(tw)
                tf = parameter_overrides.get("formation_time_s", parameter_overrides.get("formationTime"))
                if tf is not None:
                    raw_config["breach"]["formation_time_s"] = float(tf)
                be = parameter_overrides.get("bottom_elevation_m", parameter_overrides.get("invertElevation"))
                if be is not None:
                    raw_config["breach"]["bottom_elevation_m"] = float(be)
            if "hydrology" in raw_config and isinstance(raw_config["hydrology"], dict):
                rl = parameter_overrides.get("initial_reservoir_level_m", parameter_overrides.get("reservoirLevel"))
                if rl is not None:
                    raw_config["hydrology"]["initial_reservoir_level_m"] = float(rl)
            if "roughness" in raw_config and isinstance(raw_config["roughness"], dict):
                mn = parameter_overrides.get("default_manning_n", parameter_overrides.get("manningN"))
                if mn is not None:
                    raw_config["roughness"]["default_manning_n"] = float(mn)

        contract = ScenarioContract(**raw_config)
        engine = get_simulation_engine(sim.solver)

        workdir = settings.OUTPUT_DIR / sim.id / "work"
        results_dir = settings.OUTPUT_DIR / sim.id / "results"
        workdir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        sim.work_dir = str(workdir)

        # Progress callback
        def on_progress(pct: float, phase: str):
            sim.progress_pct = round(pct, 1)
            sim.current_phase = phase
            db.commit()

        # 1. Prepare
        engine.prepare(contract, workdir)

        # 2. Run hydrodynamic solver
        exec_summary = engine.run(contract, workdir, progress_callback=on_progress)

        # 3. Parse and normalize results
        on_progress(88.0, "Generating standardized GIS products (GeoTIFF, GeoJSON)")
        normalized_summary = engine.parse_and_normalize(contract, workdir, results_dir)

        # 4. Save result records
        sim.metrics_summary = exec_summary.metrics
        for ptype in ["max_depth", "max_velocity", "arrival_time"]:
            tif_file = results_dir / f"{ptype}.tif"
            if tif_file.exists():
                res_rec = SimulationResult(
                    simulation_id=sim.id,
                    product_type=ptype,
                    file_path=str(tif_file),
                    media_type="image/tiff",
                    crs=contract.domain.crs,
                    min_value=0.0,
                    max_value=float(exec_summary.metrics.get(f"{ptype}_m", 10.0)),
                )
                db.add(res_rec)

        # 5. Spatial impact analysis
        on_progress(95.0, "Intersecting with settlement and road infrastructure")
        assets = db.query(ExposureAsset).filter(ExposureAsset.project_id == scenario_orm.project_id).all()
        asset_dicts = [
            {
                "asset_type": a.asset_type,
                "name": a.name,
                "geom_geojson": a.geom_geojson,
                "properties": a.properties,
            }
            for a in assets
        ]

        import numpy as np
        sim_data = np.load(workdir / "raw_simulation.npz")
        max_depth_arr = sim_data["max_depth"]
        arr_arr = sim_data["arrival_time"]
        bounds = sim_data["extent"].tolist()

        extent_geojson_path = results_dir / "flood_extent.geojson"
        with open(extent_geojson_path, "r", encoding="utf-8") as f:
            extent_geojson = json.load(f)

        max_vel_arr = sim_data["max_velocity"] if "max_velocity" in sim_data else None

        impact_data = compute_spatial_impacts(
            simulation_id=sim.id,
            extent_geojson=extent_geojson,
            max_depth_raster=max_depth_arr,
            arrival_time_raster=arr_arr,
            exposure_assets=asset_dicts,
            bounds=bounds,
            max_velocity_raster=max_vel_arr,
        )
        sim.metrics_summary["impact"] = impact_data.model_dump()

        # Mark completed
        sim.status = "completed"
        sim.progress_pct = 100.0
        sim.current_phase = "Simulation finished successfully"
        sim.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
        if sim:
            sim.status = "failed"
            sim.error_message = str(e)
            sim.current_phase = "Failed"
            db.commit()
    finally:
        db.close()


@router.post("/run", response_model=SimulationResponse, status_code=202)
def run_simulation(
    req: SimulationRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    scen = db.query(Scenario).filter(Scenario.id == req.scenario_id).first()
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario {req.scenario_id} not found")

    solver_choice = req.solvers[0] if req.solvers else "fast_swe"
    sim = Simulation(
        scenario_id=req.scenario_id,
        solver=solver_choice,
        status="queued",
        progress_pct=0.0,
        current_phase="Queued in task worker",
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    # Dispatch to background task worker
    from backend.database import SessionLocal
    if req.async_mode:
        background_tasks.add_task(execute_simulation_job, sim.id, SessionLocal, req.parameter_overrides)
    else:
        # Run synchronously if requested
        execute_simulation_job(sim.id, SessionLocal, req.parameter_overrides)
        db.refresh(sim)

    return sim

@router.get("/latest", response_model=Optional[SimulationResponse])
def get_latest_simulation(scenario_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Simulation).filter(Simulation.status == "completed")
    if scenario_id:
        query = query.filter(Simulation.scenario_id == scenario_id)
    sim = query.order_by(Simulation.created_at.desc()).first()
    return sim

@router.get("/{simulation_id}", response_model=SimulationResponse)
def get_simulation(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    return sim

@router.get("/{simulation_id}/status", response_model=SimulationStatusResponse)
def get_simulation_status(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    return sim

@router.get("/{simulation_id}/impact", response_model=ImpactResponse)
def get_simulation_impact(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    impact_dict = sim.metrics_summary.get("impact")
    if not impact_dict:
        # Fallback to compute if results exist
        results_dir = settings.OUTPUT_DIR / sim.id / "results"
        extent_path = results_dir / "flood_extent.geojson"
        if extent_path.exists():
            with open(extent_path) as f:
                extent_geojson = json.load(f)
            import numpy as np
            workdir = settings.OUTPUT_DIR / sim.id / "work"
            data = np.load(workdir / "raw_simulation.npz")
            max_vel_arr = data["max_velocity"] if "max_velocity" in data else None
            impact_res = compute_spatial_impacts(
                simulation_id=sim.id,
                extent_geojson=extent_geojson,
                max_depth_raster=data["max_depth"],
                arrival_time_raster=data["arrival_time"],
                exposure_assets=[],
                bounds=data["extent"].tolist(),
                max_velocity_raster=max_vel_arr,
            )
            return impact_res
        raise HTTPException(status_code=400, detail="Impact analysis not yet available. Ensure simulation is completed.")
    return ImpactResponse(**impact_dict)

@router.get("/{simulation_id}/flood_extent.geojson")
def get_simulation_extent_geojson(simulation_id: str):
    geojson_path = settings.OUTPUT_DIR / simulation_id / "results" / "flood_extent.geojson"
    if not geojson_path.exists():
        raise HTTPException(status_code=404, detail="Flood extent GeoJSON not found")
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/{simulation_id}/layers/{product_type}")
def get_simulation_raster_layer(simulation_id: str, product_type: str):
    tif_path = settings.OUTPUT_DIR / simulation_id / "results" / f"{product_type}.tif"
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail=f"Layer {product_type}.tif not found")
    return FileResponse(tif_path, media_type="image/tiff", filename=f"{product_type}.tif")

@router.get("/{simulation_id}/timeline")
def get_simulation_timeline(simulation_id: str):
    """
    Returns time series slices with depth arrays and metadata for web map animation.
    """
    workdir = settings.OUTPUT_DIR / simulation_id / "work"
    results_dir = settings.OUTPUT_DIR / simulation_id / "results"
    raw_npz = workdir / "raw_simulation.npz"
    if not raw_npz.exists():
        raise HTTPException(status_code=404, detail="Simulation timeline data not found")

    import numpy as np
    data = np.load(raw_npz)
    times = data["times"].tolist()
    bounds = data["extent"].tolist()
    depths = data["depths"]
    max_d = float(np.max(data["max_depth"]))

    # Downsample time slices slightly for fast web playback payload
    slices = []
    for idx, t in enumerate(times):
        d_slice = depths[idx]
        wet_cells = int(np.count_nonzero(d_slice > 0.1))
        slices.append({
            "step": idx,
            "time_s": float(t),
            "time_min": round(float(t) / 60.0, 1),
            "flooded_cells": wet_cells,
            "max_step_depth": round(float(np.max(d_slice)), 2),
        })

    # Check for precomputed timeline_extents.json
    timeline_extents_path = results_dir / "timeline_extents.json"
    step_geojsons = {}
    if timeline_extents_path.exists():
        try:
            with open(timeline_extents_path, "r", encoding="utf-8") as f:
                step_geojsons = json.load(f)
        except Exception:
            pass

    return {
        "simulation_id": simulation_id,
        "bounds": bounds,
        "total_steps": len(slices),
        "max_overall_depth_m": max_d,
        "slices": slices,
        "step_geojsons": step_geojsons,
    }

@router.get("/{simulation_id}/step/{step}.geojson")
def get_simulation_step_geojson(simulation_id: str, step: int):
    results_dir = settings.OUTPUT_DIR / simulation_id / "results"
    timeline_extents_path = results_dir / "timeline_extents.json"
    if timeline_extents_path.exists():
        with open(timeline_extents_path, "r", encoding="utf-8") as f:
            extents = json.load(f)
            if str(step) in extents:
                return extents[str(step)]

    fallback = results_dir / "flood_extent.geojson"
    if fallback.exists():
        with open(fallback, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Step GeoJSON not found")

