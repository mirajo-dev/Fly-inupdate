from __future__ import annotations

from dataclasses import dataclass, field

from algo_A_star import RoutePlan
from parsing.network import Connection, Network


@dataclass
class DroneState:
    """Runtime state of one drone."""

    drone_id: int
    route: tuple[str, ...]
    step: int = 0
    delivered: bool = False
    transit_connection: tuple[str, str] | None = None
    transit_remaining: int = 0
    last_move: tuple[str, str] | None = None

    @property
    def current_zone(self) -> str:
        """Return the current zone, or the departure zone while in transit."""
        return self.route[self.step]


@dataclass(frozen=True)
class Movement:
    """A movement recorded during a simulation turn."""

    drone_id: int
    source: str
    destination: str
    turns: int


@dataclass
class TurnResult:
    """All movements produced by one simulation turn."""

    turn: int
    movements: list[Movement] = field(default_factory=list)


class Simulation:
    """Discrete-turn simulator enforcing zone and link capacities."""

    def __init__(self, network: Network, plan: RoutePlan) -> None:
        if len(plan.routes) != network.nb_drones:
            raise ValueError("Route plan does not contain one route per drone.")

        self.network = network
        self.plan = plan
        self.drones = [
            DroneState(index + 1, route)
            for index, route in enumerate(plan.routes)
        ]
        self.turn = 0
        self.history: list[TurnResult] = []
        self._connection_by_key = self._build_connection_index()

    def _build_connection_index(self) -> dict[frozenset[str], Connection]:
        """Index connections independently of their direction."""
        return {
            frozenset((conn.zone_a, conn.zone_b)): conn
            for conn in self.network.connections
        }

    def _connection(self, source: str, destination: str) -> Connection:
        """Get a connection or raise a clear internal error."""
        key = frozenset((source, destination))
        try:
            return self._connection_by_key[key]
        except KeyError as exc:
            raise ValueError(
                f"Missing connection between '{source}' and '{destination}'"
            ) from exc

    def _zone_counts(self) -> dict[str, int]:
        """Count drones occupying normal zones at the start of a turn."""
        counts = {name: 0 for name in self.network.zones}
        for drone in self.drones:
            if not drone.delivered and drone.transit_connection is None:
                counts[drone.current_zone] += 1
        return counts

    def _transit_counts(self) -> dict[frozenset[str], int]:
        """Count drones currently using each connection."""
        counts: dict[frozenset[str], int] = {}
        for drone in self.drones:
            if drone.transit_connection is not None:
                key = frozenset(drone.transit_connection)
                counts[key] = counts.get(key, 0) + 1
        return counts

    def _finish_restricted_moves(self, result: TurnResult) -> None:
        """Complete restricted movements whose two-turn travel has elapsed."""
        for drone in self.drones:
            if drone.transit_connection is None:
                continue
            drone.transit_remaining -= 1
            if drone.transit_remaining > 0:
                continue

            destination = drone.transit_connection[1]
            drone.step += 1
            drone.transit_connection = None
            drone.last_move = (drone.route[drone.step - 1], destination)
            if destination == self.network.end:
                drone.delivered = True

            result.movements.append(
                Movement(
                    drone.drone_id,
                    drone.route[drone.step - 1],
                    destination,
                    2,
                )
            )

    def _can_enter(
        self,
        destination: str,
        zone_counts: dict[str, int],
        outgoing: dict[str, int],
    ) -> bool:
        """Check destination capacity after same-turn departures."""
        if destination == self.network.end:
            return True
        zone = self.network.zones[destination]
        available = zone_counts[destination] - outgoing.get(destination, 0)
        return available < zone.max_drones

    def _select_moves(
        self,
        zone_counts: dict[str, int],
        transit_counts: dict[frozenset[str], int],
    ) -> list[DroneState]:
        """Select simultaneous one-turn moves without exceeding capacities."""
        proposals: list[DroneState] = []
        outgoing: dict[str, int] = {}

        # Prefer priority destinations, then shorter remaining routes.
        candidates = [
            drone
            for drone in self.drones
            if not drone.delivered and drone.transit_connection is None
            and drone.step < len(drone.route) - 1
        ]
        candidates.sort(
            key=lambda drone: (
                0 if self.network.zones[drone.route[drone.step + 1]].zone_type == "priority" else 1,
                len(drone.route) - drone.step,
                drone.drone_id,
            )
        )

        reserved_links: dict[frozenset[str], int] = {}
        for drone in candidates:
            source = drone.current_zone
            destination = drone.route[drone.step + 1]
            connection = self._connection(source, destination)
            key = frozenset((source, destination))
            current_link = transit_counts.get(key, 0) + reserved_links.get(key, 0)
            if current_link >= connection.max_link_capacity:
                continue

            zone = self.network.zones[destination]
            if zone.zone_type == "blocked":
                continue

            if not self._can_enter(destination, zone_counts, outgoing):
                continue

            proposals.append(drone)
            outgoing[source] = outgoing.get(source, 0) + 1
            reserved_links[key] = reserved_links.get(key, 0) + 1

        return proposals

    def step_once(self) -> TurnResult:
        """Advance the simulation by exactly one discrete turn."""
        if self.finished:
            return TurnResult(self.turn, [])

        self.turn += 1
        result = TurnResult(self.turn)
        self._finish_restricted_moves(result)

        zone_counts = self._zone_counts()
        transit_counts = self._transit_counts()
        selected = self._select_moves(zone_counts, transit_counts)

        for drone in selected:
            source = drone.current_zone
            destination = drone.route[drone.step + 1]
            zone_type = self.network.zones[destination].zone_type
            if zone_type == "restricted":
                drone.transit_connection = (source, destination)
                drone.transit_remaining = 2
            else:
                drone.step += 1
                drone.last_move = (source, destination)
                if destination == self.network.end:
                    drone.delivered = True
                result.movements.append(
                    Movement(drone.drone_id, source, destination, 1)
                )

        self.history.append(result)
        return result

    def run_to_end(self, max_turns: int = 10000) -> list[TurnResult]:
        """Run until all drones arrive or a safety limit is reached."""
        while not self.finished:
            if self.turn >= max_turns:
                raise RuntimeError("Simulation exceeded the maximum turn limit.")
            self.step_once()
        return self.history

    @property
    def finished(self) -> bool:
        """Return True when every drone has reached the end."""
        return all(drone.delivered for drone in self.drones)
