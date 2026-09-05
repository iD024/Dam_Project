from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np
from pathlib import Path
from backend.database import get_db
from backend.config import settings
from backend.models import Simulation, ObservedFlood, Validation
from backend.schemas.api_schemas import ValidationResponse
from backend.services.satellite.gee_service import generate_sentinel1_observed_flood
from backend.services.validation_service import calculate_flood_validation_metrics

router = APIRouter(prefix="/validation", tags=["Validation"])

@router.get("/{simulation_id}", response_model=ValidationResponse)
def get_or_run_validation(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    workdir = settings.OUTPUT_DIR / sim.id / "work"
    raw_npz = workdir / "raw_simulation.npz"
    if not raw_npz.exists():
        raise HTTPException(status_code=400, detail="Simulation output not available for validation")

    data = np.load(raw_npz)
    pred_depth = data["max_depth"]
    bounds = data["extent"].tolist()
    pred_mask = pred_depth > 0.10

    # Retrieve or generate Sentinel-1 observed mask
    obs_geojson, obs_mask = generate_sentinel1_observed_flood(bounds, nx=pred_depth.shape[1], ny=pred_depth.shape[0])

    val_response = calculate_flood_validation_metrics(
        simulation_id=sim.id,
        observed_flood_id="obs_sentinel1_default",
        pred_mask=pred_mask,
        obs_mask=obs_mask,
    )
    return val_response

@router.get("/satellite/observed_flood/{project_id}")
def get_observed_satellite_flood(project_id: str, db: Session = Depends(get_db)):
    # Bounding box for Tehri / Bhagirathi study area
    bounds = [78.45, 30.12, 78.65, 30.40]
    geojson_feature_col, _ = generate_sentinel1_observed_flood(bounds)
    return geojson_feature_col
