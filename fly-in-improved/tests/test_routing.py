from __future__ import annotations

from pathlib import Path

from algo_A_star import RoutePlanner
from parsing.network import NetworkParser
from simulation import Simulation


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "parsing" / "maps"


def test_weighted_path_exists() -> None:
    """A weighted route must be found on the priority puzzle."""
    path = MAPS / "medium" / "03_priority_puzzle.txt"
    network = NetworkParser(str(path)).parse()
    candidate = RoutePlanner(network).shortest_path()
    assert candidate is not None
    assert candidate.zones[0] == network.start
    assert candidate.zones[-1] == network.end


def test_simulation_delivers_all_drones() -> None:
    """The linear reference map should finish without deadlock."""
    path = MAPS / "easy" / "01_linear_path.txt"
    network = NetworkParser(str(path)).parse()
    plan = RoutePlanner(network).build_plan()
    simulation = Simulation(network, plan)
    simulation.run_to_end(max_turns=100)
    assert simulation.finished
    assert simulation.turn > 0
