"""Parsing and validation of ``connection`` directives.

Defines the ``Connection`` dataclass, the line parser
``parse_connection_line`` and the ``ConnexionConfig`` accumulator.
Running the module directly prints the parsed connections.
"""

from parse_hub_config import Zone, HubConfig
from metadata import parse_metadata, ensure_known_keys, converted_to_integer
from read_config import ReadFile, OneLine
import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Connection:
    """Represents an undirected connection between two zones.

    Attributes:
        zone_a: Name of the first endpoint.
        zone_b: Name of the second endpoint.
        max_link_capacity: Maximum number of drones allowed to use the
            connection during a single turn.
        count_line: Line number that defined the connection.
    """

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1
    count_line: int = 0

    def get_zones(self) -> tuple[str, str]:
        """Returns the two endpoints in their declared order.

        Returns:
            Tuple ``(zone_a, zone_b)`` containing the names of both zones.
        """
        return self.zone_a, self.zone_b

    def get_key(self) -> str:
        """Builds a text key identifying the connection.

        Returns:
            String of the form ``Connection:zone_a-zone_b``.
        """
        return f"Connection:{self.zone_a}-{self.zone_b}"


def parse_connection_line(rest: str, count_line: int) -> Connection:
    """Parses a connection definition into a ``Connection`` object.

    The basic format is ``<zone1>-<zone2>`` with an optional metadata
    block. The function rejects self-connections and validates the
    ``max_link_capacity`` value (default: 1).

    Args:
        rest: Part of the line located after the ``connection`` directive.
        count_line: Source line number.

    Returns:
        Validated ``Connection`` object.

    Raises:
        ValueError: If the metadata block is malformed, if the
            connection format is invalid, if both endpoints are
            identical, if a metadata key is unknown, or if the capacity
            is not a positive integer.
        SystemExit: If the metadata block itself is invalid (see
            ``parse_metadata``). An error message is printed first.
    """
    rest = rest.strip()
    bracket_idx = rest.find("[")
    if bracket_idx == -1:
        head, meta_raw = rest, ""
    else:
        if not rest.endswith("]"):
            raise ValueError(
                f"Line {count_line}: malformed metadata block in '{rest}'")
        head, meta_raw = rest[:bracket_idx].strip(), rest[bracket_idx:]

    parts = head.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Line {count_line}: invalid connection '{head}', "
            "expected '<zone1>-<zone2>'"
        )
    zone_a, zone_b = parts
    if zone_a == zone_b:
        raise ValueError(
            f"Line {count_line}: a zone cannot connect to itself ('{zone_a}')")

    metadata = parse_metadata(meta_raw, count_line)
    ensure_known_keys(metadata, {"max_link_capacity"}, count_line)
    capacity = converted_to_integer(
        metadata.get("max_link_capacity", "1"), "max_link_capacity", count_line
    )

    return Connection(
        zone_a=zone_a,
        zone_b=zone_b,
        max_link_capacity=capacity,
        count_line=count_line)


class ConnexionConfig:
    """Manages the connections defined between the network's zones.

    The configuration keeps the list of connections and a dictionary of
    normalized keys, which allows duplicates to be detected regardless
    of the order of the endpoints.

    Attributes:
        _zones: Dictionary of known zones, used to check references.
        connections: List of valid connections.
        _seen: Mapping from the (unordered) pair of endpoints of each
            connection already encountered to its source line number.
    """

    def __init__(self, zones: dict[str, Zone]) -> None:
        """Initializes a connection configuration.

        Args:
            zones: Dictionary of already-declared zones. Connections must
                reference only these zones.
        """
        self._zones = zones
        self.connections: list[Connection] = []
        self._seen: dict[frozenset[str], int] = {}

    def add_connection_entry(self, entry: OneLine) -> None:
        """Parses, validates and adds a connection.

        Each endpoint must exist in the zone dictionary. A ``frozenset`` key
        is used to detect duplicates regardless of the order
        ``zone_a-zone_b`` or ``zone_b-zone_a``. The valid connection is
        appended to ``connections``.

        Args:
            entry: Configuration line containing the connection directive.

        Raises:
            ValueError: If the connection has already been declared.
            SystemExit: If the connection line cannot be parsed or if it
                references an undefined zone. An error message is printed
                before exiting.
        """
        try:
            conn = parse_connection_line(entry.value, entry.count_line)
        except ValueError as e:
            print(f"Error :{e}")
            sys.exit(1)

        for name in (conn.zone_a, conn.zone_b):
            if name not in self._zones:
                print(
                    f"Line {entry.count_line}: connection references undefined"
                    f" (or not-yet-defined) zone '{name}'"
                )
                sys.exit(1)

        key = frozenset((conn.zone_a, conn.zone_b))
        if key in self._seen:
            raise ValueError(
                f"Line {entry.count_line}: duplicate connection "
                f"'{conn.zone_a}-{conn.zone_b}'"
                f" (already defined line {self._seen[key]})"
            )
        self._seen[key] = entry.count_line
        self.connections.append(conn)


if __name__ == "__main__":
    try:
        entries = ReadFile.read_config(sys.argv[1])
        hub_config = HubConfig()
        connexion_config = ConnexionConfig(hub_config.zones)
        for entry in entries:
            if entry.key in HubConfig.KIND_BY_KEY:
                hub_config.add_zone_entry(entry)
            elif entry.key == "connection":
                connexion_config.add_connection_entry(entry)
        for conn in connexion_config.connections:
            print(conn)
    except Exception as e:
        print(e)
        sys.exit(1)
