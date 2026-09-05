from backend.simulation_engines.base import SimulationEngine, ExecutionSummary
from backend.simulation_engines.fast_swe.solver import FastSWE2DEngine
from backend.simulation_engines.dflowfm.adapter import DFlowFMEngine
from backend.simulation_engines.sph.adapter import DualSPHysicsEngine

def get_simulation_engine(solver_name: str) -> SimulationEngine:
    name_lower = solver_name.lower()
    if name_lower in ["dflowfm", "delft3d", "delft3d_fm"]:
        return DFlowFMEngine()
    elif name_lower in ["sph", "dualsphysics"]:
        return DualSPHysicsEngine()
    elif name_lower in ["fast_swe", "swe", "default"]:
        return FastSWE2DEngine()
    else:
        raise ValueError(f"Unknown simulation solver: {solver_name}. Supported: dflowfm, dualsphysics, fast_swe")

__all__ = [
    "SimulationEngine",
    "ExecutionSummary",
    "FastSWE2DEngine",
    "DFlowFMEngine",
    "DualSPHysicsEngine",
    "get_simulation_engine",
]
