import optuna
from typing import Dict, Any, List, Tuple
import numpy as np

def run_satellite_calibration(
    observed_mask: np.ndarray,
    baseline_scenario: Dict[str, Any],
    n_trials: int = 15,
) -> Dict[str, Any]:
    """
    Optimizes Manning roughness and breach width against Sentinel-1 SAR
    observed flood mask using Bayesian optimization (Optuna).
    Objective: Minimize J = (1 - IoU) + 0.25 * FPR + 0.25 * FNR
    """
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    ny, nx = observed_mask.shape
    obs_bool = observed_mask.astype(bool)

    trials_log = []

    def objective(trial: optuna.Trial) -> float:
        manning_n = trial.suggest_float("manning_n", 0.025, 0.090)
        breach_width = trial.suggest_float("breach_width_m", 50.0, 150.0)

        # Synthetic rapid 2D response mapping for optimization trial
        # Higher breach width -> wider inundation; higher Manning n -> slower flow, higher local depths
        x = np.linspace(0, 1, nx)
        y = np.linspace(0, 1, ny)
        X, Y = np.meshgrid(x, y)
        
        thalweg_x = 0.5 + 0.15 * np.sin(2.5 * np.pi * Y)
        dist = np.abs(X - thalweg_x)

        # Predicted flood boundary for trial parameters
        spread_factor = (breach_width / 100.0) * (1.0 + (manning_n - 0.04) * 5.0)
        pred_mask = dist < (0.12 * spread_factor)

        # Calculate metrics
        tp = int(np.count_nonzero(pred_mask & obs_bool))
        fp = int(np.count_nonzero(pred_mask & ~obs_bool))
        fn = int(np.count_nonzero(~pred_mask & obs_bool))

        denom = tp + fp + fn
        iou = tp / denom if denom > 0 else 0.0
        fpr = fp / max(fp + (nx * ny - tp - fp - fn), 1)
        fnr = fn / max(fn + tp, 1)

        loss = (1.0 - iou) + 0.25 * fpr + 0.25 * fnr

        trials_log.append({
            "trial_number": trial.number,
            "manning_n": round(manning_n, 4),
            "breach_width_m": round(breach_width, 1),
            "iou": round(iou, 4),
            "loss": round(loss, 4),
        })
        return loss

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    best_iou = 1.0 - (study.best_value)

    return {
        "status": "completed",
        "best_manning_n": round(best_params["manning_n"], 4),
        "best_breach_width_m": round(best_params["breach_width_m"], 1),
        "optimized_iou": round(max(0.0, min(1.0, 1.0 - study.best_value)), 4),
        "total_trials": len(study.trials),
        "trials": trials_log,
    }
