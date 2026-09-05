import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.database import get_db
from backend.models import Scenario, Project
from backend.schemas.api_schemas import ScenarioCreate, ScenarioResponse, AIInputCheckResponse
from backend.schemas.scenario_contract import ScenarioContract
from backend.services.ai.input_quality import check_scenario_input_quality

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    return scen

@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(req: ScenarioCreate, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == req.project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project {req.project_id} not found")

    cfg_dict = req.engine_config.model_dump()
    cfg_json = json.dumps(cfg_dict, sort_keys=True)
    scen_hash = hashlib.sha256(cfg_json.encode("utf-8")).hexdigest()

    scen = Scenario(
        project_id=req.project_id,
        dam_id=req.dam_id,
        river_id=req.river_id,
        name=req.name,
        description=req.description,
        status="validated",
        engine_config=cfg_dict,
        scenario_hash=scen_hash,
    )
    db.add(scen)
    db.commit()
    db.refresh(scen)
    return scen

@router.post("/{scenario_id}/validate", response_model=AIInputCheckResponse)
def validate_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

    contract = ScenarioContract(**scen.engine_config)
    check_result = check_scenario_input_quality(contract)
    scen.status = check_result.overall_status.lower()
    db.commit()
    return check_result
