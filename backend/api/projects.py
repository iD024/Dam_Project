from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.database import get_db
from backend.models import Project, Dam, River, ExposureAsset, Scenario
from backend.schemas.api_schemas import (
    ProjectCreate,
    ProjectResponse,
    DamResponse,
    RiverResponse,
    ScenarioResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()

@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(req: ProjectCreate, db: Session = Depends(get_db)):
    proj = Project(name=req.name, description=req.description)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return proj

@router.get("/{project_id}/dams", response_model=List[DamResponse])
def get_project_dams(project_id: str, db: Session = Depends(get_db)):
    return db.query(Dam).filter(Dam.project_id == project_id).all()

@router.get("/{project_id}/rivers", response_model=List[RiverResponse])
def get_project_rivers(project_id: str, db: Session = Depends(get_db)):
    return db.query(River).filter(River.project_id == project_id).all()

@router.get("/{project_id}/scenarios", response_model=List[ScenarioResponse])
def get_project_scenarios(project_id: str, db: Session = Depends(get_db)):
    return db.query(Scenario).filter(Scenario.project_id == project_id).all()

@router.get("/{project_id}/assets")
def get_project_exposure_assets(project_id: str, db: Session = Depends(get_db)):
    assets = db.query(ExposureAsset).filter(ExposureAsset.project_id == project_id).all()
    features = []
    for a in assets:
        features.append({
            "type": "Feature",
            "id": a.id,
            "geometry": a.geom_geojson,
            "properties": {
                "id": a.id,
                "asset_type": a.asset_type,
                "name": a.name,
                "source": a.source,
                **a.properties,
            }
        })
    return {"type": "FeatureCollection", "features": features}
