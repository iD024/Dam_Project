import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db
from backend.services.seed_demo_data import seed_database_if_empty

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    seed_database_if_empty()

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "fast_swe" in data["supported_solvers"]

def test_list_projects():
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("Tehri" in p["name"] for p in data)

def test_get_project_dams():
    response = client.get("/api/v1/projects")
    data = response.json()
    tehri_proj = [p for p in data if "Tehri" in p["name"]][0]
    proj_id = tehri_proj["id"]
    dams_res = client.get(f"/api/v1/projects/{proj_id}/dams")
    assert dams_res.status_code == 200
    dams = dams_res.json()
    assert len(dams) >= 1
    assert dams[0]["name"] == "Tehri Dam"

def test_ai_parameter_recommendation_endpoint():
    payload = {
        "dam_height_m": 260.5,
        "reservoir_storage_m3": 3.54e9,
        "dam_type": "embankment",
        "failure_mode": "overtopping",
    }
    response = client.post("/api/v1/ai/parameter-recommendation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_breach_width_m"] > 50.0
    assert "Froehlich" in data["method"]

def test_full_simulation_run_impact_and_validation():
    # 1. Get existing Tehri scenario
    scens_res = client.get("/api/v1/projects/proj_tehri_001/scenarios")
    assert scens_res.status_code == 200
    scens = scens_res.json()
    assert len(scens) >= 1
    scen_id = scens[0]["id"]

    # 2. Run simulation
    run_payload = {
        "scenario_id": scen_id,
        "solvers": ["fast_swe"],
        "async_mode": False,  # Synchronous for test verification
    }
    run_res = client.post("/api/v1/simulations/run", json=run_payload)
    assert run_res.status_code == 202
    sim_data = run_res.json()
    sim_id = sim_data["id"]
    assert sim_data["status"] == "completed"

    # 3. Check status
    status_res = client.get(f"/api/v1/simulations/{sim_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["progress_pct"] == 100.0

    # 4. Check spatial impact
    impact_res = client.get(f"/api/v1/simulations/{sim_id}/impact")
    assert impact_res.status_code == 200
    impact = impact_res.json()
    assert impact["affected_villages_count"] > 0
    assert impact["max_depth_m"] > 0

    # 5. Check validation against satellite
    val_res = client.get(f"/api/v1/validation/{sim_id}")
    assert val_res.status_code == 200
    val = val_res.json()
    assert "iou" in val
    assert 0.0 <= val["iou"] <= 1.0

    # 6. Check AI Result Interpreter
    ai_query = {
        "simulation_id": sim_id,
        "query": "Which villages are inundated?",
    }
    ai_res = client.post("/api/v1/ai/result-interpretation", json=ai_query)
    assert ai_res.status_code == 200
    assert "village" in ai_res.json()["answer"].lower()

    # 7. Check GeoJSON and export
    geojson_res = client.get(f"/api/v1/simulations/{sim_id}/flood_extent.geojson")
    assert geojson_res.status_code == 200
    assert geojson_res.json()["type"] == "FeatureCollection"

    export_res = client.post(f"/api/v1/exports/{sim_id}?format=kml")
    assert export_res.status_code == 200
    assert export_res.json()["status"] == "completed"

def test_simulation_run_with_parameter_overrides():
    scens_res = client.get("/api/v1/projects/proj_tehri_001/scenarios")
    scen_id = scens_res.json()[0]["id"]

    run_payload = {
        "scenario_id": scen_id,
        "solvers": ["fast_swe"],
        "async_mode": False,
        "parameter_overrides": {
            "breachWidth": 120.0,
            "topWidth": 170.0,
            "formationTime": 180.0,
            "reservoirLevel": 830.0,
            "manningN": 0.035,
        }
    }
    run_res = client.post("/api/v1/simulations/run", json=run_payload)
    assert run_res.status_code == 202
    sim_data = run_res.json()
    assert sim_data["status"] == "completed"
    assert sim_data["metrics_summary"]["max_depth_m"] > 0

