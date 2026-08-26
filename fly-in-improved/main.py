from __future__ import annotations

import sys

from algo_A_star import RoutePlanner
from display import SimulationApp
from parsing.network import NetworkParser


def main() -> int:
    """Parse a map and start the graphical simulation."""
    if len(sys.argv) != 2:
        print("Usage: python3 main.py <map_file>")
        return 1

    try:
        network = NetworkParser(sys.argv[1]).parse()
        planner = RoutePlanner(network)
        plan = planner.build_plan()
        print(f"Initial routes: {len(plan.routes)} candidate route(s)")
        app = SimulationApp(network, plan)
        app.run()
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
