import pytest
from pathlib import Path
import tempfile
from backend.schemas.scenario_contract import ScenarioContract
from backend.simulation_engines.fast_swe.solver import FastSWE2DEngine

def test_fast_swe_simulation_and_normalization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        workdir = Path(tmp_dir) / "work"
        out_dir = Path(tmp_dir) / "results"

        scenario_data = {
            "schema_version": "1.0.0",
            "project_id": "proj_test_swe",
            "dam_id": "dam_test_01",
            "river_id": "riv_test_01",
            "domain": {
                "bbox": [78.45, 30.12, 78.65, 30.40],
                "crs": "EPSG:4326"
            },
            "terrain": {
                "dem_uri": "synthetic",
                "resolution_m": 30.0
            },
            "hydrology": {
                "initial_reservoir_level_m": 820.0,
                "initial_storage_m3": 5e7, # 50 Million m3
            },
            "roughness": {
                "default_manning_n": 0.040
            },
            "breach": {
                "type": "trapezoidal_progressive",
                "failure_mode": "overtopping",
                "start_s": 0.0,
                "formation_time_s": 60.0,
                "bottom_width_m": 80.0,
                "top_width_m": 120.0,
                "side_slope_hv": 1.0,
                "bottom_elevation_m": 750.0
            },
            "numerics": {
                "simulation_duration_s": 300.0, # 5 min test
                "output_interval_s": 60.0,
                "max_courant": 0.85,
                "dry_threshold_m": 0.01
            }
        }
        contract = ScenarioContract(**scenario_data)
        engine = FastSWE2DEngine()

        # Validation check
        is_valid, errors = engine.validate(contract)
        assert is_valid is True
        assert len(errors) == 0

        # Preparation
        engine.prepare(contract, workdir)
        assert workdir.exists()

        # Run
        summary = engine.run(contract, workdir)
        assert summary.status == "completed"
        assert summary.exit_code == 0
        assert "max_depth_m" in summary.metrics
        assert summary.metrics["max_depth_m"] > 0
        assert summary.metrics["total_water_released_m3"] > 0

        # Normalization
        norm_summary = engine.parse_and_normalize(contract, workdir, out_dir)
        assert out_dir.exists()
        assert (out_dir / "max_depth.tif").exists()
        assert (out_dir / "max_velocity.tif").exists()
        assert (out_dir / "arrival_time.tif").exists()
        assert (out_dir / "flood_extent.geojson").exists()
        assert (out_dir / "summary.json").exists()

        assert norm_summary["max_depth_m"] > 0
