from __future__ import annotations

from dataclasses import dataclass

from parsing.metadata import (
    converted_to_integer,
    ensure_known_keys,
    parse_metadata,
)
from parsing.read_config import OneLine


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
FORBIDDEN_NAME_CHARS = {"-", " "}


@dataclass(frozen=True)
class Zone:
    """A network zone."""

    name: str
    x: int
    y: int
    kind: str
    zone_type: str = "normal"
    color: str | None = None
    max_drones: int = 1
    count_line: int = 0


def _validate_name(name: str, line_no: int) -> None:
    """Validate a zone name according to the subject."""
    if not name:
        raise ValueError(f"Line {line_no}: zone name is empty")
    if any(char.isspace() for char in name):
        raise ValueError(
            f"Line {line_no}: zone name '{name}' cannot contain spaces"
        )
    if "-" in name:
        raise ValueError(
            f"Line {line_no}: zone name '{name}' cannot contain a dash"
        )


def parse_zone_line(kind: str, rest: str, line_no: int) -> Zone:
    """Parse a start_hub, hub, or end_hub declaration."""
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

    tokens = head.split()
    if len(tokens) != 3:
        raise ValueError(
            f"Line {line_no}: expected '<name> <x> <y>'"
        )

    name, x_raw, y_raw = tokens
    _validate_name(name, line_no)

    try:
        x = int(x_raw)
        y = int(y_raw)
    except ValueError as exc:
        raise ValueError(
            f"Line {line_no}: coordinates must be integers"
        ) from exc

    metadata = parse_metadata(metadata_raw, line_no)
    ensure_known_keys(metadata, {"zone", "color", "max_drones"}, line_no)

    zone_type = metadata.get("zone", "normal")
    if zone_type not in VALID_ZONE_TYPES:
        raise ValueError(
            f"Line {line_no}: invalid zone type '{zone_type}'"
        )

    color = metadata.get("color")
    max_drones = converted_to_integer(
        metadata.get("max_drones", "1"),
        "max_drones",
        line_no,
    )

    return Zone(
        name=name,
        x=x,
        y=y,
        kind=kind,
        zone_type=zone_type,
        color=color,
        max_drones=max_drones,
        count_line=line_no,
    )


class HubConfig:
    """Collect and validate all zones."""

    KIND_BY_KEY = {
        "start_hub": "start",
        "hub": "normal",
        "end_hub": "end",
    }

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.start_name: str | None = None
        self.end_name: str | None = None

    def add_zone_entry(self, entry: OneLine) -> None:
        """Add one zone declaration."""
        zone = parse_zone_line(
            self.KIND_BY_KEY[entry.key],
            entry.value,
            entry.count_line,
        )
        if zone.name in self.zones:
            previous = self.zones[zone.name]
            raise ValueError(
                f"Line {entry.count_line}: duplicate zone '{zone.name}' "
                f"(already defined on line {previous.count_line})"
            )

        if zone.kind == "start":
            if self.start_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple start_hub declarations"
                )
            self.start_name = zone.name
        elif zone.kind == "end":
            if self.end_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple end_hub declarations"
                )
            self.end_name = zone.name

        self.zones[zone.name] = zone

    def validate(self) -> None:
        """Require exactly one start and one end."""
        if self.start_name is None:
            raise ValueError("No start_hub defined in the file.")
        if self.end_name is None:
            raise ValueError("No end_hub defined in the file.")
