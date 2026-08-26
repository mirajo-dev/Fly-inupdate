from __future__ import annotations

from dataclasses import dataclass

from parsing.metadata import (
    converted_to_integer,
    ensure_known_keys,
    parse_metadata,
)
from parsing.parse_hub_config import Zone
from parsing.read_config import OneLine


@dataclass(frozen=True)
class Connection:
    """A bidirectional link between two zones."""

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1
    count_line: int = 0


def parse_connection_line(rest: str, line_no: int) -> Connection:
    """Parse '<zone1>-<zone2> [max_link_capacity=N]'."""
    rest = rest.strip()
    bracket_index = rest.find("[")
    if bracket_index == -1:
        head, metadata_raw = rest, ""
    else:
        head = rest[:bracket_index].strip()
        metadata_raw = rest[bracket_index:]
        if not metadata_raw.endswith("]"):
            raise ValueError(
                f"Line {line_no}: malformed metadata block"
            )

    parts = head.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Line {line_no}: invalid connection '{head}', "
            "expected '<zone1>-<zone2>'"
        )

    zone_a, zone_b = parts
    if zone_a == zone_b:
        raise ValueError(
            f"Line {line_no}: a zone cannot connect to itself"
        )

    metadata = parse_metadata(metadata_raw, line_no)
    ensure_known_keys(metadata, {"max_link_capacity"}, line_no)
    capacity = converted_to_integer(
        metadata.get("max_link_capacity", "1"),
        "max_link_capacity",
        line_no,
    )

    return Connection(zone_a, zone_b, capacity, line_no)


class ConnexionConfig:
    """Validate and collect connections."""

    def __init__(self, zones: dict[str, Zone]) -> None:
        self._zones = zones
        self.connections: list[Connection] = []
        self._seen: dict[frozenset[str], int] = {}

    def add_connection_entry(self, entry: OneLine) -> None:
        """Add a connection after validating its endpoints."""
        connection = parse_connection_line(entry.value, entry.count_line)

        for name in (connection.zone_a, connection.zone_b):
            if name not in self._zones:
                raise ValueError(
                    f"Line {entry.count_line}: connection references "
                    f"undefined or not-yet-defined zone '{name}'"
                )

        key = frozenset((connection.zone_a, connection.zone_b))
        if key in self._seen:
            raise ValueError(
                f"Line {entry.count_line}: duplicate connection "
                f"'{connection.zone_a}-{connection.zone_b}'"
            )

        self._seen[key] = entry.count_line
        self.connections.append(connection)
