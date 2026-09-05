from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from backend.database import get_db
from backend.config import settings
from backend.models import Simulation, ExportRecord
from backend.services.export_service import export_simulation_products

router = APIRouter(prefix="/exports", tags=["Exports"])

@router.post("/{simulation_id}")
def generate_export(
    simulation_id: str,
    format: str = Query(..., description="Export format: geojson, kml, shp, geotiff, csv"),
    db: Session = Depends(get_db),
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")

    results_dir = settings.OUTPUT_DIR / sim.id / "results"
    export_dir = settings.OUTPUT_DIR / sim.id / "exports"

    try:
        exported_path = export_simulation_products(
            simulation_id=sim.id,
            export_format=format,
            results_dir=results_dir,
            output_dir=export_dir,
            summary_data=sim.metrics_summary,
        )
        rec = ExportRecord(
            simulation_id=sim.id,
            format=format.lower(),
            file_path=str(exported_path),
            file_size_bytes=exported_path.stat().st_size if exported_path.exists() else 0,
            status="completed",
        )
        db.add(rec)
        db.commit()
        return {
            "status": "completed",
            "format": format.lower(),
            "filename": exported_path.name,
            "download_url": f"/api/v1/exports/{simulation_id}/download?format={format.lower()}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/{simulation_id}/download")
def download_export(
    simulation_id: str,
    format: str = Query(..., description="Export format: geojson, kml, shp, geotiff, csv"),
    db: Session = Depends(get_db),
):
    export_dir = settings.OUTPUT_DIR / simulation_id / "exports"
    fmt = format.lower()
    if fmt == "geojson":
        fpath = export_dir / f"flood_extent_{simulation_id}.geojson"
        media = "application/geo+json"
    elif fmt == "kml":
        fpath = export_dir / f"flood_extent_{simulation_id}.kml"
        media = "application/vnd.google-earth.kml+xml"
    elif fmt in ["shp", "shapefile"]:
        fpath = export_dir / f"flood_extent_{simulation_id}_shp.zip"
        media = "application/zip"
    elif fmt in ["geotiff", "tif"]:
        fpath = export_dir / f"flood_rasters_{simulation_id}.zip"
        media = "application/zip"
    elif fmt == "csv":
        fpath = export_dir / f"summary_{simulation_id}.csv"
        media = "text/csv"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format {format}")

    if not fpath.exists():
        # Try generating it on the fly
        results_dir = settings.OUTPUT_DIR / simulation_id / "results"
        if not results_dir.exists():
            raise HTTPException(status_code=404, detail="Simulation results not found")
        fpath = export_simulation_products(
            simulation_id=simulation_id,
            export_format=format,
            results_dir=results_dir,
            output_dir=export_dir,
            summary_data={},
        )

    return FileResponse(fpath, media_type=media, filename=fpath.name)
