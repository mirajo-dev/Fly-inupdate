"""Network model and top-level parser for Fly-in configuration files.

``NetworkParser`` dispatches each directive to the specialized
parsers and assembles the resulting ``Network``. Running the module
directly prints a summary of the parsed network.
"""

from parse_connexion import ConnexionConfig, Connection
from parse_hub_config import HubConfig, Zone
from parse_nb_drone import DroneConfig
from read_config import ReadFile
import sys
import os
from dataclasses import dataclass
from parse_nb_drone import Drone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


KNOWN_KEYS = {"nb_drones", "start_hub", "hub", "end_hub", "connection"}


@dataclass
class Network:
    """Represents the complete network used by the solver and the simulation.

    The network groups together the number of drones, the zones, the
    start and end zones, and the list of connections.

    Attributes:
        nb_drones: Number of drones to simulate.
        zones: Dictionary of zones indexed by name.
        start: Name of the start zone.
        end: Name of the end zone.
        connections: List of connections between zones.
    """

    nb_drones: int
    zones: dict[str, Zone]
    start: str
    end: str
    connections: list[Connection]

    def get_drones(self) -> list[Drone]:
        """Creates the list of drones initialized at the start zone.

        Identifiers are generated sequentially in the form ``D1``, ``D2``,
        etc. Each drone receives the same start and destination as the
        network.

        Returns:
            List containing exactly ``nb_drones`` ``Drone`` objects.
        """
        drones = []
        for i in range(1, self.nb_drones + 1):
            drones.append(Drone(
                id_drone=f"D{i}",
                current_zone=self.start,
                goal_zone=self.end))
        return drones

    def get_zone(self, name: str) -> Zone:
        """Looks up a network zone by its name.

        Args:
            name: Name of the zone to look up.

        Returns:
            ``Zone`` object matching the given name.

        Raises:
            ValueError: If no zone has this name.
        """
        for name_zone, zone in self.zones.items():
            if name_zone == name:
                return zone
        raise ValueError(f"NetworkError: Zone '{name}' not found.")

    def get_connection(self, hub_a: str, hub_b: str) -> Connection:
        """Looks up a connection between two zones in the given order.

        Args:
            hub_a: Name of the first zone.
            hub_b: Name of the second zone.

        Returns:
            Connection whose ``get_zones()`` matches exactly the tuple
            ``(hub_a, hub_b)``.

        Raises:
            ValueError: If no matching connection is found.
        """
        for conn in self.connections:
            if conn.get_zones() == (hub_a, hub_b):
                return conn
        raise ValueError(
            f"NetworkError: Connection '{hub_a}-{hub_b}' not found.")


class NetworkParser:
    """Parses a configuration file and builds a ``Network`` object.

    The parser delegates line reading to ``ReadFile``, drone-count
    validation to ``DroneConfig``, zone validation to ``HubConfig``, and
    connection validation to ``ConnexionConfig``.

    Attributes:
        filename: Path of the configuration file to analyze.
    """

    def __init__(self, filename: str) -> None:
        """Initializes the parser with the file path.

        Args:
            filename: Path to the network configuration file.
        """
        self.filename = filename

    def parse(self) -> Network:
        """Reads, validates and assembles the complete network configuration.

        Directives are dispatched to the specialized components according to
        their key, then the zone configuration is validated before the final
        network is built.

        Returns:
            ``Network`` object containing the number of drones, the zones,
            the start and end zones, and the connections.

        Raises:
            ValueError: If the drone configuration is empty or duplicated,
                if a start or end hub is missing or declared twice, or if a
                connection is duplicated.
            SystemExit: If the file cannot be read, if a directive is
                unknown, or if a line is malformed. An error message is
                printed before exiting.
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
                    f"Line {
                        entry.count_line}: unknown directive '{
                        entry.key}', " f"expected one of {
                        sorted(KNOWN_KEYS)}")
                sys.exit(1)

        hub_config.validate()

        if hub_config.start_name is None or hub_config.end_name is None:
            raise ValueError("Network configuration is missing start/end.")

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
