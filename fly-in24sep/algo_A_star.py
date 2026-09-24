"""Path-finding helpers for the Fly-in drone network.

Provides a Euclidean distance heuristic, a neighbor lookup, and an
enumeration of candidate simple paths between the start and end zones.
"""

from math import sqrt
from collections import deque
from network import Network


def calculate_heuristic(
    zone1_name: str, zone2_name: str,
    network: Network
) -> float:
    """Computes the Euclidean distance between two zones.

    Args:
        zone1_name: Name of the first zone.
        zone2_name: Name of the second zone.
        network: Network holding the zones and their coordinates.

    Returns:
        Straight-line distance between the two zones, in map units.

    Raises:
        KeyError: If one of the zone names is not defined in the network.
    """
    z1 = network.zones[zone1_name]
    z2 = network.zones[zone2_name]
    return sqrt((z2.x - z1.x) ** 2 + (z2.y - z1.y) ** 2)


def get_valid_neighbors(current_zone: str, network: Network) -> list[str]:
    """Lists the zones directly connected to a given zone.

    Connections are treated as undirected. The zone type (for example
    ``blocked``) is not taken into account by this function.

    Args:
        current_zone: Name of the zone whose neighbors are requested.
        network: Network holding the connections.

    Returns:
        Names of the neighboring zones, in the order the connections
        were declared.
    """
    neighbors = []
    for conn in network.connections:
        if conn.zone_a == current_zone:
            neighbors.append(conn.zone_b)
        elif conn.zone_b == current_zone:
            neighbors.append(conn.zone_a)
    return neighbors


def find_all_paths(network: Network) -> list[list[str]]:
    """Enumerates candidate simple paths from the start to the end zone.

    The network is explored breadth-first and a zone is never visited
    twice on the same path. Once a first path has been found, any partial
    path that is more than three zones longer than that first path is
    discarded. The resulting paths are sorted by number of zones, then by
    total Euclidean length.

    Args:
        network: Network to explore.

    Returns:
        List of paths, each one being a list of zone names going from
        ``network.start`` to ``network.end``. The list is empty when the
        end zone cannot be reached.
    """
    start = network.start
    end = network.end
    paths = []

    queue = deque([(start, [start])])

    while queue:
        current, path = queue.popleft()

        if current == end:
            paths.append(path)
            continue

        if len(paths) > 0 and len(path) > len(paths[0]) + 3:
            continue

        for neighbor in get_valid_neighbors(current, network):
            if neighbor not in path:
                queue.append((neighbor, path + [neighbor]))

    def path_cost(p: list[str]) -> tuple[int, float]:
        """Computes the sort key of a path.

        Args:
            p: Path expressed as a list of zone names.

        Returns:
            Tuple ``(number of zones, total Euclidean length)``. Paths with
            fewer zones come first; the length breaks ties.
        """
        cost = 0.0
        for i in range(len(p) - 1):
            cost += calculate_heuristic(p[i], p[i + 1], network)
        return (len(p), cost)

    paths.sort(key=path_cost)
    return paths
