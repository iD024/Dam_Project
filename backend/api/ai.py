from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Simulation
from backend.schemas.api_schemas import (
    AIInputCheckRequest,
    AIInputCheckResponse,
    AIParameterRecommendationRequest,
    AIParameterRecommendationResponse,
    AIResultInterpretationRequest,
    AIResultInterpretationResponse,
)
from backend.services.ai.input_quality import check_scenario_input_quality
from backend.services.ai.parameter_recommender import recommend_breach_parameters
from backend.services.ai.result_interpreter import interpret_simulation_results
from backend.services.ai.surrogate import run_surrogate_inference
from backend.services.ai.calibration import run_satellite_calibration
from backend.services.satellite.gee_service import generate_sentinel1_observed_flood

router = APIRouter(prefix="/ai", tags=["AI Services"])

@router.post("/input-check", response_model=AIInputCheckResponse)
def api_check_inputs(req: AIInputCheckRequest):
    return check_scenario_input_quality(req.scenario)

@router.post("/parameter-recommendation", response_model=AIParameterRecommendationResponse)
def api_recommend_parameters(req: AIParameterRecommendationRequest):
    return recommend_breach_parameters(req)

@router.post("/result-interpretation", response_model=AIResultInterpretationResponse)
def api_interpret_results(req: AIResultInterpretationRequest, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == req.simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {req.simulation_id} not found")

    impact_data = sim.metrics_summary.get("impact", {})
    metrics = sim.metrics_summary
    return interpret_simulation_results(metrics, impact_data, req.query)

@router.post("/surrogate")
def api_surrogate_inference(req: AIInputCheckRequest):
    return run_surrogate_inference(req.scenario)

@router.post("/calibration/{simulation_id}")
def api_calibrate_model(simulation_id: str, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    bounds = [78.45, 30.12, 78.65, 30.40]
    _, obs_mask = generate_sentinel1_observed_flood(bounds, nx=60, ny=80)
    calib_result = run_satellite_calibration(obs_mask, sim.scenario.engine_config, n_trials=10)
    return calib_result
