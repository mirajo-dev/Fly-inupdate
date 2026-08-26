from __future__ import annotations

from dataclasses import dataclass

from parsing.parse_connexion import Connection, ConnexionConfig
from parsing.parse_hub_config import HubConfig, Zone
from parsing.parse_nb_drone import DroneConfig
from parsing.read_config import ReadFile


@dataclass(frozen=True)
class Network:
    """Complete parsed drone network."""

    nb_drones: int
    zones: dict[str, Zone]
    start: str
    end: str
    connections: list[Connection]


class NetworkParser:
    """Parse a Fly-in Drones map."""

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def parse(self) -> Network:
        """Parse and validate the complete map."""
        entries = ReadFile.read_config(self.filename)
        drone_config = DroneConfig(entries)
        hubs = HubConfig()

        for entry in entries:
            if entry.key in HubConfig.KIND_BY_KEY:
                hubs.add_zone_entry(entry)
            elif entry.key == "nb_drones":
                continue

        hubs.validate()

        connections = ConnexionConfig(hubs.zones)
        for entry in entries:
            if entry.key == "connection":
                connections.add_connection_entry(entry)
            elif entry.key not in {"nb_drones", *HubConfig.KIND_BY_KEY}:
                raise ValueError(
                    f"Line {entry.count_line}: unknown directive '{entry.key}'"
                )

        return Network(
            nb_drones=drone_config.get_nb_drone(),
            zones=hubs.zones,
            start=hubs.start_name or "",
            end=hubs.end_name or "",
            connections=connections.connections,
        )
