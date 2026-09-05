import pytest
from backend.schemas.scenario_contract import ScenarioContract

def test_valid_scenario_contract():
    scenario_data = {
        "schema_version": "1.0.0",
        "project_id": "proj_test_01",
        "dam_id": "dam_test_01",
        "river_id": "riv_test_01",
        "scenario_name": "Test Breach",
        "domain": {
            "bbox": [78.0, 30.0, 78.5, 30.5],
            "crs": "EPSG:4326"
        },
        "terrain": {
            "dem_uri": "data/demo/tehri/dem.tif",
            "resolution_m": 30.0
        },
        "hydrology": {
            "initial_reservoir_level_m": 820.0,
            "initial_storage_m3": 1e9,
        },
        "roughness": {
            "source": "landcover",
            "default_manning_n": 0.04
        },
        "breach": {
            "type": "trapezoidal_progressive",
            "failure_mode": "overtopping",
            "formation_time_s": 180.0,
            "bottom_width_m": 80.0,
            "top_width_m": 120.0,
            "side_slope_hv": 1.0,
            "bottom_elevation_m": 760.0
        }
    }
    contract = ScenarioContract(**scenario_data)
    assert contract.project_id == "proj_test_01"
    assert contract.breach.bottom_width_m == 80.0
    assert contract.breach.top_width_m == 120.0

def test_invalid_breach_widths():
    scenario_data = {
        "schema_version": "1.0.0",
        "project_id": "proj_test_01",
        "dam_id": "dam_test_01",
        "river_id": "riv_test_01",
        "domain": {"bbox": [78.0, 30.0, 78.5, 30.5]},
        "terrain": {"dem_uri": "data/demo/tehri/dem.tif"},
        "hydrology": {"initial_reservoir_level_m": 820.0, "initial_storage_m3": 1e9},
        "roughness": {},
        "breach": {
            "bottom_width_m": 100.0,
            "top_width_m": 80.0,  # Invalid: top width smaller than bottom width
            "bottom_elevation_m": 760.0
        }
    }
    with pytest.raises(Exception):
        ScenarioContract(**scenario_data)

def test_invalid_bbox():
    scenario_data = {
        "schema_version": "1.0.0",
        "project_id": "proj_test_01",
        "dam_id": "dam_test_01",
        "river_id": "riv_test_01",
        "domain": {"bbox": [78.5, 30.5, 78.0, 30.0]},  # Inverted bbox
        "terrain": {"dem_uri": "data/demo/tehri/dem.tif"},
        "hydrology": {"initial_reservoir_level_m": 820.0, "initial_storage_m3": 1e9},
        "roughness": {},
        "breach": {"bottom_width_m": 50.0, "top_width_m": 80.0, "bottom_elevation_m": 760.0}
    }
    with pytest.raises(Exception):
        ScenarioContract(**scenario_data)
