import numpy as np
from backend.schemas.api_schemas import AIParameterRecommendationRequest
from backend.services.ai.parameter_recommender import recommend_breach_parameters
from backend.services.validation_service import calculate_flood_validation_metrics

def test_ai_breach_parameter_recommendations():
    req = AIParameterRecommendationRequest(
        dam_height_m=260.5,
        reservoir_storage_m3=3.54e9,
        dam_type="embankment",
        failure_mode="overtopping",
    )
    res = recommend_breach_parameters(req)
    assert res.recommended_breach_width_m > 50.0
    assert res.breach_width_range_m[0] < res.recommended_breach_width_m < res.breach_width_range_m[1]
    assert res.recommended_formation_time_s > 60.0
    assert res.peak_discharge_est_m3s > 1000.0
    assert len(res.citations) >= 2

def test_validation_metrics_calculation():
    pred = np.zeros((10, 10), dtype=bool)
    obs = np.zeros((10, 10), dtype=bool)

    # Overlap 4 cells (TP), pred has 2 extra (FP), obs has 2 extra (FN)
    pred[2:4, 2:4] = True  # 4 cells
    pred[2:4, 4] = True    # 2 FP cells -> total 6 pred

    obs[2:4, 2:4] = True   # 4 cells
    obs[4, 2:4] = True     # 2 FN cells -> total 6 obs

    # TP = 4, FP = 2, FN = 2. Denom = 4 + 2 + 2 = 8. IoU = 4/8 = 0.50
    metrics = calculate_flood_validation_metrics(
        simulation_id="sim_val_test",
        observed_flood_id="obs_test",
        pred_mask=pred,
        obs_mask=obs,
    )
    assert metrics.iou == 0.50
    assert metrics.csi == 0.50
    assert metrics.confusion_matrix["tp_cells"] == 4
    assert metrics.confusion_matrix["fp_cells"] == 2
    assert metrics.confusion_matrix["fn_cells"] == 2
