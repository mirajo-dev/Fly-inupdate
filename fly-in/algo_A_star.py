from math import sqrt
from collections import deque
from parsing.network import Network


def calculate_heuristic(zone1_name: str, zone2_name: str, network: Network) -> float:
    z1 = network.zones[zone1_name]
    z2 = network.zones[zone2_name]
    return sqrt((z2.x - z1.x) ** 2 + (z2.y - z1.y) ** 2)


def get_valid_neighbors(current_zone: str, network: Network) -> list[str]:
    neighbors = []
    for conn in network.connections:
        if conn.zone_a == current_zone:
            neighbors.append(conn.zone_b)
        elif conn.zone_b == current_zone:
            neighbors.append(conn.zone_a)
    return neighbors


def find_all_paths(network: Network) -> list[list[str]]:
    """Trouve tous les chemins simples de network.start à network.end, triés par longueur/coût."""
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

    def path_cost(p):
        cost = 0.0
        for i in range(len(p) - 1):
            cost += calculate_heuristic(p[i], p[i + 1], network)
        return (len(p), cost)

    paths.sort(key=path_cost)
    return paths