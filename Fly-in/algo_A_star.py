from math import sqrt
import heapq
from parsing.network import Network


def calculate_heuristic(zone1_name: str, zone2_name: str, network: Network) -> float:
    """Calcule la distance à vol d'oiseau entre deux hubs."""
    z1 = network.zones[zone1_name]
    z2 = network.zones[zone2_name]
    return sqrt((z2.x - z1.x) ** 2 + (z2.y - z1.y) ** 2)


def get_valid_neighbors(current_zone: str, network: Network) -> list[str]:
    """Récupère tous les hubs reliés à la zone actuelle."""
    neighbors = []
    for conn in network.connections:
        if conn.zone_a == current_zone:
            neighbors.append(conn.zone_b)
        elif conn.zone_b == current_zone:
            neighbors.append(conn.zone_a)
    return neighbors


def reconstruct_path(came_from: dict[str, str], start_zone: str, end_zone: str) -> list[str]:
    """Reconstruit la liste des zones depuis l'arrivée jusqu'au départ."""
    path = []
    current = end_zone
    while current != start_zone:
        path.append(current)
        current = came_from[current]
    path.append(start_zone)
    return path[::-1]


def a_star(network: Network) -> list[str]:
    """Algorithme A* principal retournant le chemin optimal [start, ..., end]."""
    start = network.start
    end = network.end

    # 1. Initialisation des coûts g (réel) et f (estimé)
    g_score = {name: float('inf') for name in network.zones}
    g_score[start] = 0

    f_score = {name: float('inf') for name in network.zones}
    f_score[start] = calculate_heuristic(start, end, network)

    # 2. File de priorité (heap) stockant des tuples: (f_score, nom_zone)
    open_set = []
    heapq.heappush(open_set, (f_score[start], start))

    came_from = {}
    visited = set()

    # 3. Boucle d'exploration
    while open_set:
        _, current = heapq.heappop(open_set)

        # Si l'objectif est atteint, on reconstruit le trajet
        if current == end:
            return reconstruct_path(came_from, start, end)

        if current in visited:
            continue
        visited.add(current)

        # Exploration de chaque voisin
        for neighbor in get_valid_neighbors(current, network):
            tentative_g = g_score[current] + 1  # Coût de 1 par saut de hub

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + calculate_heuristic(neighbor, end, network)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []  # Retourne une liste vide si aucun chemin n'existe