from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from backend.schemas.scenario_contract import ScenarioContract

class ExecutionSummary:
    def __init__(
        self,
        simulation_id: str,
        solver: str,
        exit_code: int = 0,
        status: str = "completed",
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        self.simulation_id = simulation_id
        self.solver = solver
        self.exit_code = exit_code
        self.status = status
        self.metrics = metrics or {}
        self.error_message = error_message

class SimulationEngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the simulation engine (e.g. fast_swe, dflowfm, dualsphysics)"""
        pass

    @abstractmethod
    def validate(self, scenario: ScenarioContract) -> tuple[bool, list[str]]:
        """Validate scenario inputs against solver constraints. Returns (is_valid, error_messages)"""
        pass

    @abstractmethod
    def prepare(self, scenario: ScenarioContract, workdir: Path) -> Path:
        """Prepare grid, boundary conditions, and solver input files in workdir"""
        pass

    @abstractmethod
    def run(
        self,
        scenario: ScenarioContract,
        workdir: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> ExecutionSummary:
        """Execute simulation with progress updates"""
        pass

    @abstractmethod
    def parse_and_normalize(
        self,
        scenario: ScenarioContract,
        workdir: Path,
        out_dir: Path,
    ) -> Dict[str, Any]:
        """Normalize raw solver output into standard GeoTIFFs, arrival time, max depth, and GeoJSON extent"""
        pass
