import sys
import os
from dataclasses import dataclass



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from .read_config import ReadFile, OneLine
from .metadata import parse_metadata, ensure_known_keys, converted_to_integer


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
FORBIDDEN_NAME_CHARS = {"-"}

@dataclass
class Zone:
    name: str
    x: int
    y: int
    kind: str
    zone_type: str = "normal"
    color: str | None = None
    max_drones: int = 1
    count_line: int = 0


def _validate_name(name: str, count_line: int) -> None:
    if name == "":
        raise ValueError(f"Line {count_line}: zone name is empty")
    if any(c.isspace() for c in name):
        raise ValueError(f"Line {count_line}: zone name '{name}' cannot contain spaces")
    if any(c in FORBIDDEN_NAME_CHARS for c in name):
        raise ValueError(f"Line {count_line}: zone name '{name}' cannot contain a dash")


def parse_zone_line(kind: str, rest: str, count_line: int) -> Zone:
    rest = rest.strip()
    bracket_idx = rest.find("[")
    if bracket_idx == -1:
        head, meta_raw = rest, ""
    else:
        if not rest.endswith("]"):
            raise ValueError(f"Line {count_line}: malformed metadata block in '{rest}'")
        head, meta_raw = rest[:bracket_idx].strip(), rest[bracket_idx:]

    tokens = head.split()
    if len(tokens) != 3:
        raise ValueError(
            f"Line {count_line}: expected '<name> <x> <y>', got '{head}'"
        )
    name, x_str, y_str = tokens
    _validate_name(name, count_line)

    try:
        x = int(x_str)
        y = int(y_str)
    except ValueError:
        raise ValueError(
            f"Line {count_line}: coordinates must be integers, got '{x_str} {y_str}'"
        )

    metadata = parse_metadata(meta_raw, count_line)
    ensure_known_keys(metadata, {"zone", "color", "max_drones"}, count_line)

    zone_type = metadata.get("zone", "normal")
    if zone_type not in VALID_ZONE_TYPES:
        raise ValueError(
            f"Line {count_line}: invalid zone type '{zone_type}', "
            f"must be one of {sorted(VALID_ZONE_TYPES)}"
        )

    color = metadata.get("color")
    if color is not None and (color == "" or any(c.isspace() for c in color)):
        raise ValueError(f"Line {count_line}: invalid color '{color}'")

    max_drones = converted_to_integer(metadata.get("max_drones", "1"), "max_drones", count_line)

    return Zone(
        name=name, x=x, y=y, kind=kind,
        zone_type=zone_type, color=color, max_drones=max_drones, count_line=count_line,
    )


class HubConfig:

    KIND_BY_KEY = {"start_hub": "start", "hub": "normal", "end_hub": "end"}

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.start_name: str | None = None
        self.end_name: str | None = None

    def add_zone_entry(self, entry: OneLine) -> None:
        kind = self.KIND_BY_KEY[entry.key]
        zone = parse_zone_line(kind, entry.value, entry.count_line)

        if zone.name in self.zones:
            raise ValueError(
                f"Line {entry.count_line}: duplicate zone name '{zone.name}' "
                f"(already defined line {self.zones[zone.name].count_line})"
            )

        if kind == "start":
            if self.start_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple start_hub declarations "
                    f"(first one line {self.zones[self.start_name].count_line})"
                )
            self.start_name = zone.name

        if kind == "end":
            if self.end_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple end_hub declarations "
                    f"(first one line {self.zones[self.end_name].count_line})"
                )
            self.end_name = zone.name

        self.zones[zone.name] = zone

    def validate(self) -> None:
        if self.start_name is None:
            raise ValueError("No start_hub defined in the file.")
        if self.end_name is None:
            raise ValueError("No end_hub defined in the file.")


if __name__ == "__main__":
    try:
        entries = ReadFile.read_config(sys.argv[1])
        hub_config = HubConfig()
        for entry in entries:
            if entry.key in HubConfig.KIND_BY_KEY:
                hub_config.add_zone_entry(entry)
        hub_config.validate()
        for name, zone in hub_config.zones.items():
            print(zone)
        print(f"start: {hub_config.start_name} / end: {hub_config.end_name}")
    except Exception as e:
        print(e)
        sys.exit(1)
