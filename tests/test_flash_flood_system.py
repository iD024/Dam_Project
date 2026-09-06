import pytest
import numpy as np
from pathlib import Path
from backend.schemas.scenario_contract import ScenarioContract, FlashFloodConfig
from backend.simulation_engines.fast_swe.solver import FastSWE2DEngine
from backend.models import Project, Scenario, Dam, ExposureAsset
from backend.database import SessionLocal
from backend.services.seed_demo_data import seed_database_if_empty

def test_flash_flood_scenario_contract_and_hydrograph():
    # Verify FlashFloodConfig schema
    ff_config = FlashFloodConfig(
        event_type="cloudburst",
        rainfall_intensity_mmh=140.0,
        catchment_area_km2=280.0,
        runoff_coefficient=0.75,
        peak_discharge_m3s=6500.0,
        surge_duration_s=1800.0,
    )
    assert ff_config.event_type == "cloudburst"
    assert ff_config.peak_discharge_m3s == 6500.0

    scenario = ScenarioContract(
        schema_version="1.0.0",
        project_id="proj_chamoli_002",
        dam_id="dam_tapovan_002",
        river_id="riv_rishi_002",
        domain={"bbox": [79.55, 30.45, 79.80, 30.65], "crs": "EPSG:4326"},
        terrain={"dem_uri": "data/demo/tehri/dem_tehri.tif", "resolution_m": 30.0},
        hydrology={"initial_reservoir_level_m": 1800.0, "initial_storage_m3": 1.2e8},
        roughness={"source": "landcover", "default_manning_n": 0.055},
        breach={"type": "trapezoidal_progressive", "bottom_width_m": 60.0, "top_width_m": 90.0, "bottom_elevation_m": 1780.0},
        flash_flood=ff_config,
        numerics={"simulation_duration_s": 300.0, "output_interval_s": 60.0},
    )
    assert scenario.flash_flood is not None
    assert scenario.flash_flood.event_type == "cloudburst"

def test_reservoir_initialized_at_t_zero(tmp_path):
    engine = FastSWE2DEngine()
    scen = ScenarioContract(
        schema_version="1.0.0",
        project_id="proj_test_reservoir",
        dam_id="dam_test_001",
        river_id="riv_test_001",
        domain={"bbox": [78.45, 30.12, 78.65, 30.40], "crs": "EPSG:4326"},
        terrain={"dem_uri": "data/demo/tehri/dem_tehri.tif", "resolution_m": 30.0},
        hydrology={"initial_reservoir_level_m": 820.0, "initial_storage_m3": 2.4e9},
        roughness={"source": "landcover", "default_manning_n": 0.042},
        breach={"type": "trapezoidal_progressive", "bottom_width_m": 80.0, "top_width_m": 120.0, "bottom_elevation_m": 750.0},
        numerics={"simulation_duration_s": 120.0, "output_interval_s": 60.0},
    )
    workdir = tmp_path / "work"
    out_dir = tmp_path / "results"
    workdir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine.prepare(scen, workdir)
    engine.run(scen, workdir)
    norm = engine.parse_and_normalize(scen, workdir, out_dir)

    raw_data = np.load(workdir / "raw_simulation.npz")
    depths = raw_data["depths"]
    # At t=0 (step 0), reservoir water MUST be present behind dam
    assert np.max(depths[0]) > 2.0
    assert np.count_nonzero(depths[0] > 0.5) > 10

from backend.database import SessionLocal, init_db
from backend.services.seed_demo_data import seed_database_if_empty

def test_rishi_ganga_chamoli_project_seeded():
    init_db()
    seed_database_if_empty()
    db = SessionLocal()
    try:
        rishi_proj = db.query(Project).filter(Project.id == "proj_chamoli_002").first()
        assert rishi_proj is not None

        # Must have dam/barrage, river, scenario, and exposure assets
        dams = db.query(Dam).filter(Dam.project_id == "proj_chamoli_002").all()
        assert len(dams) > 0

        scens = db.query(Scenario).filter(Scenario.project_id == "proj_chamoli_002").all()
        assert len(scens) > 0
        assert scens[0].engine_config.get("flash_flood") is not None or "flash flood" in scens[0].name.lower()

        assets = db.query(ExposureAsset).filter(ExposureAsset.project_id == "proj_chamoli_002").all()
        assert len(assets) >= 4
    finally:
        db.close()

def test_chamoli_simulation_produces_chamoli_coordinates_and_water_features(tmp_path):
    import json
    engine = FastSWE2DEngine()
    scen = ScenarioContract(
        schema_version="1.0.0",
        project_id="proj_chamoli_002",
        dam_id="dam_tapovan_002",
        river_id="riv_rishi_002",
        scenario_name="Rishi Ganga Alpine Flash Flood",
        domain={"bbox": [79.55, 30.45, 79.75, 30.58], "crs": "EPSG:4326"},
        terrain={"dem_uri": "data/demo/chamoli/dem.tif", "resolution_m": 30.0},
        hydrology={"initial_reservoir_level_m": 1800.0, "initial_storage_m3": 1.45e7},
        roughness={"source": "landcover", "default_manning_n": 0.055},
        breach={"type": "trapezoidal_progressive", "bottom_width_m": 60.0, "top_width_m": 90.0, "bottom_elevation_m": 1780.0},
        flash_flood={
            "event_type": "flash_flood",
            "rainfall_intensity_mmh": 125.0,
            "catchment_area_km2": 320.0,
            "runoff_coefficient": 0.85,
            "peak_discharge_m3s": 8500.0,
            "surge_duration_s": 1200.0,
        },
        numerics={"simulation_duration_s": 120.0, "output_interval_s": 60.0},
    )
    workdir = tmp_path / "chamoli_work"
    out_dir = tmp_path / "chamoli_results"
    workdir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine.prepare(scen, workdir)
    engine.run(scen, workdir)
    norm = engine.parse_and_normalize(scen, workdir, out_dir)

    raw_data = np.load(workdir / "raw_simulation.npz")
    extent = raw_data["extent"]
    # Coordinates must be in Chamoli [79.55, 30.45, 79.75, 30.58], NOT Tehri 78.48!
    assert extent[0] >= 79.50
    assert extent[2] <= 79.80

    with open(out_dir / "flood_extent.geojson") as f:
        geo = json.load(f)
    assert len(geo["features"]) > 0
    # Must have active water coordinates in Chamoli corridor
    first_feat = geo["features"][0]
    coords = first_feat["geometry"]["coordinates"]
    assert len(coords) > 0
    # Check that sample coordinate is indeed in Chamoli (> 79.5 lon)
    sample_lon = coords[0][0][0] if isinstance(coords[0][0][0], (int, float)) else coords[0][0][0][0]
    assert sample_lon > 79.5, f"Expected Chamoli lon > 79.5, got {sample_lon}"

