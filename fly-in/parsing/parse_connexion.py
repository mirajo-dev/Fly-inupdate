import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .read_config import ReadFile, OneLine
from .metadata import parse_metadata, ensure_known_keys, converted_to_integer
from .parse_hub_config import Zone, HubConfig


@dataclass
class Connection:
    zone_a: str
    zone_b: str
    max_link_capacity: int = 1
    count_line: int = 0


def parse_connection_line(rest: str, count_line: int) -> Connection:
    rest = rest.strip()
    bracket_idx = rest.find("[")
    if bracket_idx == -1:
        head, meta_raw = rest, ""
    else:
        if not rest.endswith("]"):
            raise ValueError(f"Line {count_line}: malformed metadata block in '{rest}'")
        head, meta_raw = rest[:bracket_idx].strip(), rest[bracket_idx:]

    parts = head.split("-")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(
            f"Line {count_line}: invalid connection '{head}', "
            "expected '<zone1>-<zone2>'"
        )
    zone_a, zone_b = parts
    if zone_a == zone_b:
        raise ValueError(f"Line {count_line}: a zone cannot connect to itself ('{zone_a}')")

    metadata = parse_metadata(meta_raw, count_line)
    ensure_known_keys(metadata, {"max_link_capacity"}, count_line)
    capacity = converted_to_integer(
        metadata.get("max_link_capacity", "1"), "max_link_capacity", count_line
    )

    return Connection(zone_a=zone_a, zone_b=zone_b, max_link_capacity=capacity, count_line=count_line)


class ConnexionConfig:

    def __init__(self, zones: dict[str, Zone]) -> None:
        self._zones = zones
        self.connections: list[Connection] = []
        self._seen: dict[frozenset, int] = {}

    def add_connection_entry(self, entry: OneLine) -> None:
        conn = parse_connection_line(entry.value, entry.count_line)

        for name in (conn.zone_a, conn.zone_b):
            if name not in self._zones:
                raise ValueError(
                    f"Line {entry.count_line}: connection references undefined "
                    f"(or not-yet-defined) zone '{name}'"
                )

        key = frozenset((conn.zone_a, conn.zone_b))
        if key in self._seen:
            raise ValueError(
                f"Line {entry.count_line}: duplicate connection "
                f"'{conn.zone_a}-{conn.zone_b}' (already defined line {self._seen[key]})"
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
