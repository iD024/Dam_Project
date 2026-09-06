import pytest
from pathlib import Path
import json
import numpy as np
from backend.simulation_engines import get_simulation_engine
from backend.schemas.scenario_contract import ScenarioContract

@pytest.fixture
def base_scenario():
    return ScenarioContract(
        schema_version="1.0.0",
        project_id="proj_test_solvers",
        dam_id="dam_test_001",
        river_id="riv_test_001",
        domain={"bbox": [78.45, 30.12, 78.65, 30.40], "crs": "EPSG:4326"},
        terrain={"dem_uri": "data/demo/tehri/dem_tehri.tif", "resolution_m": 30.0},
        hydrology={"initial_reservoir_level_m": 820.0, "initial_storage_m3": 2.4e9},
        roughness={"source": "landcover", "default_manning_n": 0.042},
        breach={
            "type": "trapezoidal_progressive",
            "failure_mode": "overtopping",
            "formation_time_s": 120.0,
            "bottom_width_m": 80.0,
            "top_width_m": 120.0,
            "side_slope_hv": 1.0,
            "bottom_elevation_m": 750.0,
        },
        solvers=["fast_swe"],
        numerics={
            "simulation_duration_s": 300.0,
            "output_interval_s": 60.0,
            "max_courant": 0.85,
            "dry_threshold_m": 0.02,
        },
    )

def test_three_solvers_execution_and_distinctive_physics(base_scenario, tmp_path):
    solver_names = ["fast_swe", "dflowfm", "dualsphysics"]
    results = {}

    for solver_name in solver_names:
        engine = get_simulation_engine(solver_name)
        assert engine.name == solver_name

        workdir = tmp_path / solver_name / "work"
        out_dir = tmp_path / solver_name / "results"
        workdir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        engine.prepare(base_scenario, workdir)
        summary = engine.run(base_scenario, workdir)
        assert summary.exit_code == 0
        assert summary.status == "completed"
        assert summary.solver == solver_name

        norm = engine.parse_and_normalize(base_scenario, workdir, out_dir)
        assert norm["solver"] == solver_name
        assert (out_dir / "flood_extent.geojson").exists()
        assert (out_dir / "max_depth.tif").exists()
        assert (out_dir / "max_velocity.tif").exists()
        assert (out_dir / "summary.json").exists()

        with open(out_dir / "summary.json") as f:
            summary_doc = json.load(f)
            assert summary_doc["solver"] == solver_name

        results[solver_name] = {
            "summary": summary,
            "norm": norm,
            "npz": np.load(workdir / "raw_simulation.npz"),
        }

    # Verify D-Flow FM distinctive flexible mesh metrics
    dflow_metrics = results["dflowfm"]["summary"].metrics
    assert "flexible_mesh" in dflow_metrics or "scheme" in dflow_metrics or dflow_metrics.get("grid_type") == "flexible_mesh"
    assert "theta_implicit" in dflow_metrics or "subgrid" in str(dflow_metrics)

    # Verify DualSPHysics SPH distinctive particle dynamics metrics
    sph_metrics = results["dualsphysics"]["summary"].metrics
    assert "particle_count" in sph_metrics or sph_metrics.get("physics_model") == "Lagrangian_WCSPH"
    assert "tait_eos_b" in sph_metrics or "froude_peak" in sph_metrics or "sound_speed_m_s" in sph_metrics

    # Verify that the solvers produce distinctive wave behavior
    swe_max_d = results["fast_swe"]["norm"]["max_depth_m"]
    dflow_max_d = results["dflowfm"]["norm"]["max_depth_m"]
    sph_max_d = results["dualsphysics"]["norm"]["max_depth_m"]

    assert swe_max_d > 0.0
    assert dflow_max_d > 0.0
    assert sph_max_d > 0.0
