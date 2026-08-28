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

    nb_drones: int
    zones: dict[str, Zone]
    start: str
    end: str
    connections: list[Connection]

    def get_drones(self) -> list[Drone]:
        drones = []
        for i in range(1, self.nb_drones + 1):
            drones.append(Drone(
                id_drone=f"D{i}",
                current_zone=self.start,
                goal_zone=self.end))
        return drones

    def get_zone(self, name: str) -> Zone:
        for name_zone, zone in self.zones.items():
            if name_zone == name:
                return zone
        raise ValueError(f"NetworkError: Zone '{name}' not found.")

class NetworkParser:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def parse(self) -> Network:
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
                raise ValueError(
                    f"Line {entry.line_no}: unknown directive '{entry.key}', "
                    f"expected one of {sorted(KNOWN_KEYS)}"
                )

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
