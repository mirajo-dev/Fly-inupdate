from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterator

from parsing.network import Connection, Network, Zone


@dataclass(frozen=True)
class PathCandidate:
    """A valid route with its weighted cost."""

    zones: tuple[str, ...]
    cost: int

    @property
    def hops(self) -> int:
        """Return the number of edges in the route."""
        return max(0, len(self.zones) - 1)


@dataclass(frozen=True)
class RoutePlan:
    """Routes assigned to individual drones."""

    routes: tuple[tuple[str, ...], ...]

    @property
    def route_count(self) -> int:
        """Return the number of routes."""
        return len(self.routes)


class RoutePlanner:
    """Find weighted routes without external graph libraries."""

    def __init__(self, network: Network) -> None:
        self.network = network
        self._adjacency = self._build_adjacency()

    def _build_adjacency(self) -> dict[str, list[Connection]]:
        """Build an adjacency table from the bidirectional connections."""
        adjacency = {name: [] for name in self.network.zones}
        for connection in self.network.connections:
            adjacency[connection.zone_a].append(connection)
            adjacency[connection.zone_b].append(connection)
        return adjacency

    def _other_end(self, connection: Connection, zone_name: str) -> str:
        """Return the opposite endpoint of a connection."""
        if connection.zone_a == zone_name:
            return connection.zone_b
        return connection.zone_a

    def _movement_cost(self, zone: Zone) -> int:
        """Return the movement cost of entering a zone."""
        if zone.zone_type == "restricted":
            return 2
        return 1

    def _neighbors(self, zone_name: str) -> Iterator[tuple[str, Connection]]:
        """Yield reachable, non-blocked neighbors."""
        for connection in self._adjacency[zone_name]:
            neighbor = self._other_end(connection, zone_name)
            if self.network.zones[neighbor].zone_type != "blocked":
                yield neighbor, connection

    def _heuristic(self, zone_name: str) -> int:
        """Return an admissible Manhattan lower bound in map coordinates."""
        current = self.network.zones[zone_name]
        target = self.network.zones[self.network.end]
        return abs(current.x - target.x) + abs(current.y - target.y)

    def shortest_path(
        self,
        start: str | None = None,
        forbidden: set[str] | None = None,
    ) -> PathCandidate | None:
        """Find a weighted shortest path with A*."""
        source = start or self.network.start
        forbidden = forbidden or set()

        if source in forbidden or self.network.end in forbidden:
            return None

        queue: list[tuple[int, int, str]] = []
        heapq.heappush(queue, (0, 0, source))
        distance = {source: 0}
        previous: dict[str, str] = {}
        counter = 0

        while queue:
            _, _, current = heapq.heappop(queue)
            if current == self.network.end:
                return self._reconstruct(previous, source, current, distance[current])

            for neighbor, _ in self._neighbors(current):
                if neighbor in forbidden:
                    continue
                zone = self.network.zones[neighbor]
                new_cost = distance[current] + self._movement_cost(zone)
                if new_cost >= distance.get(neighbor, 10**9):
                    continue

                distance[neighbor] = new_cost
                previous[neighbor] = current
                # Priority zones get a deterministic tie-break preference.
                priority_bonus = -1 if zone.zone_type == "priority" else 0
                counter += 1
                estimate = new_cost + self._heuristic(neighbor)
                heapq.heappush(
                    queue,
                    (estimate, priority_bonus, neighbor),
                )

        return None

    def _reconstruct(
        self,
        previous: dict[str, str],
        source: str,
        target: str,
        cost: int,
    ) -> PathCandidate:
        """Reconstruct a path from A* predecessor information."""
        path = [target]
        current = target
        while current != source:
            current = previous[current]
            path.append(current)
        path.reverse()
        return PathCandidate(tuple(path), cost)

    def candidates(self, limit: int = 8) -> list[PathCandidate]:
        """Generate several useful route alternatives.

        Alternatives are obtained by temporarily forbidding one internal
        zone of the current best path. This is deliberately simple and keeps
        graph logic inside the project.
        """
        if limit < 1:
            raise ValueError("limit must be positive")

        result: list[PathCandidate] = []
        seen: set[tuple[str, ...]] = set()
        best = self.shortest_path()
        if best is None:
            return []

        pending = [best]
        while pending and len(result) < limit:
            candidate = pending.pop(0)
            if candidate.zones in seen:
                continue
            seen.add(candidate.zones)
            result.append(candidate)

            internal = candidate.zones[1:-1]
            for zone_name in internal:
                alternative = self.shortest_path(forbidden={zone_name})
                if alternative and alternative.zones not in seen:
                    pending.append(alternative)

            pending.sort(key=lambda item: (item.cost, item.hops))

        return result

    def build_plan(self) -> RoutePlan:
        """Assign drones to candidate paths using a throughput-oriented score."""
        candidates = self.candidates(limit=8)
        if not candidates:
            raise ValueError(
                f"No valid path exists from '{self.network.start}' "
                f"to '{self.network.end}'"
            )

        loads = [0] * len(candidates)
        routes: list[tuple[str, ...]] = []
        for _ in range(self.network.nb_drones):
            best_index = min(
                range(len(candidates)),
                key=lambda index: (
                    candidates[index].cost + loads[index] * max(1, candidates[index].hops),
                    candidates[index].cost,
                    candidates[index].hops,
                ),
            )
            loads[best_index] += 1
            routes.append(candidates[best_index].zones)

        return RoutePlan(tuple(routes))


def a_star(network: Network) -> list[str]:
    """Compatibility wrapper returning the best route as a list."""
    planner = RoutePlanner(network)
    candidate = planner.shortest_path()
    return list(candidate.zones) if candidate else []
