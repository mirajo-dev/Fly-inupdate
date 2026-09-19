import sys
import os
from dataclasses import dataclass
from parsing.parse_nb_drone import Drone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsing.read_config import ReadFile
from parsing.parse_nb_drone import DroneConfig
from parsing.parse_hub_config import HubConfig, Zone
from parsing.parse_connexion import ConnexionConfig, Connection

KNOWN_KEYS = {"nb_drones", "start_hub", "hub", "end_hub", "connection"}


@dataclass
class Network:

    """Représente le réseau complet utilisé par le solveur et la simulation.

Le réseau regroupe le nombre de drones, les zones, les zones de départ et
d'arrivée et la liste des connexions.

Attributes:
    nb_drones: Nombre de drones à simuler.
    zones: Dictionnaire des zones indexées par leur nom.
    start: Nom de la zone de départ.
    end: Nom de la zone d'arrivée.
    connections: Liste des connexions entre zones.
"""
    nb_drones: int
    zones: dict[str, Zone]
    start: str
    end: str
    connections: list[Connection]

    def get_drones(self) -> list[Drone]:
        """Crée la liste des drones initialisés sur la zone de départ.

Les identifiants sont générés séquentiellement sous la forme ``D1``, ``D2``, etc.
Chaque drone reçoit le même départ et la même destination que le réseau.

Returns:
    Liste contenant exactement ``nb_drones`` objets ``Drone``.
"""
        drones = []
        for i in range(1, self.nb_drones + 1):
            drones.append(Drone(
                id_drone=f"D{i}",
                current_zone=self.start,
                goal_zone=self.end))
        return drones

    def get_zone(self, name: str) -> Zone:
        """Recherche une zone du réseau par son nom.

Args:
    name: Nom de la zone recherchée.

Returns:
    Objet ``Zone`` correspondant au nom fourni.

Raises:
    ValueError: Si aucune zone ne porte ce nom.
"""
        for name_zone, zone in self.zones.items():
            if name_zone == name:
                return zone
        raise ValueError(f"NetworkError: Zone '{name}' not found.")

    def get_connection(self, hub_a: str, hub_b: str) -> Connection:
        """Recherche une connexion entre deux zones dans le sens fourni.

Args:
    hub_a: Nom de la première zone.
    hub_b: Nom de la seconde zone.

Returns:
    Connexion dont ``get_zones()`` correspond exactement au tuple
    ``(hub_a, hub_b)``. Retourne implicitement ``None`` si aucune connexion
    correspondante n'est trouvée.
"""
        for conn in self.connections:
            if conn.get_zones() == (hub_a, hub_b):
                return conn


class NetworkParser:
    """Parse un fichier de configuration et construit un objet ``Network``.

Le parseur délègue la lecture des lignes à ``ReadFile``, la validation du nombre
de drones à ``DroneConfig``, celle des zones à ``HubConfig`` et celle des
connexions à ``ConnexionConfig``.

Attributes:
    filename: Chemin du fichier de configuration à analyser.
"""
    def __init__(self, filename: str) -> None:
        """Initialise le parseur avec le chemin du fichier.

Args:
    filename: Chemin vers le fichier de configuration du réseau.
"""
        self.filename = filename

    def parse(self) -> Network:
        """Lit, valide et assemble la configuration complète du réseau.

Les directives sont distribuées aux composants spécialisés selon leur clé, puis
la configuration des zones est validée avant la construction du réseau final.

Returns:
    Objet ``Network`` contenant les drones, zones, départ, arrivée et connexions.

Raises:
    ValueError: Si une directive est inconnue ou si une partie de la configuration
        est invalide, dupliquée ou incomplète.
    OSError: Si le fichier de configuration ne peut pas être lu.
"""
        entries = ReadFile.read_config(self.filename)

        drone_config = DroneConfig(entries)
        hub_config = HubConfig()
        connexion_config = ConnexionConfig(hub_config.zones)

        for entry in entries:
            if entry.key == "nb_drones":
                continue
            elif entry.key in HubConfig.KIND_BY_KEY:
                hub_config.add_zone_entry(entry)
            elif entry.key == "connection":
                connexion_config.add_connection_entry(entry)
            else:
                print(
                    f"Line {entry.count_line}: unknown directive '{entry.key}', "
                    f"expected one of {sorted(KNOWN_KEYS)}"
                )
                sys.exit(1)

        hub_config.validate()

        return Network(
            nb_drones=drone_config.get_nb_drone(),
            zones=hub_config.zones,
            start=hub_config.start_name,
            end=hub_config.end_name,
            connections=connexion_config.connections,
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 network.py <map_file>")
        sys.exit(1)
    try:
        network = NetworkParser(sys.argv[1]).parse()
        print(f"nb_drones: {network.nb_drones}")
        print(f"start: {network.start} / end: {network.end}")
        print(f"zones ({len(network.zones)}):")
        for zone in network.zones.values():
            print(f"  {zone}")
        print(f"connections ({len(network.connections)}):")
        for conn in network.connections:
            print(f"  {conn}")
    except ValueError as e:
        print(f"Parsing error: {e}")
        sys.exit(1)
