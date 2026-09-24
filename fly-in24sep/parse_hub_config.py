"""Parsing and validation of ``start_hub``, ``hub`` and ``end_hub`` lines.

Defines the ``Zone`` dataclass, the line parser ``parse_zone_line``
and the ``HubConfig`` accumulator. Running the module directly prints
the parsed zones.
"""

from metadata import parse_metadata, ensure_known_keys, converted_to_integer
from read_config import ReadFile, OneLine
import sys
import os
from dataclasses import dataclass


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
FORBIDDEN_NAME_CHARS = {"-"}


@dataclass
class Zone:
    """Describes a network zone and its capacity constraints.

    Attributes:
        name: Unique name of the zone.
        x: Horizontal coordinate on the map.
        y: Vertical coordinate on the map.
        kind: Structural role of the zone: ``start``, ``normal`` or
            ``end``.
        zone_type: Functional type of the zone (``normal``, ``blocked``,
            ``restricted`` or ``priority``).
        color: Optional color used for graphical rendering.
        max_drones: Maximum number of drones allowed in the zone.
        count_line: Configuration line number that defined the zone.
    """

    name: str
    x: int
    y: int
    kind: str
    zone_type: str = "normal"
    color: str | None = None
    max_drones: int = 1
    count_line: int = 0


def _validate_name(name: str, count_line: int) -> None:
    """Validates a zone name against the format's constraints.

    The only rule currently enforced is that the name must not contain a
    dash, which avoids any ambiguity with the ``<zone1>-<zone2>``
    connection syntax.

    Args:
        name: Zone name to check.
        count_line: Line number used in error messages.

    Raises:
        SystemExit: If the name contains a dash. An error message is
            printed before exiting.
    """
    if any(c in FORBIDDEN_NAME_CHARS for c in name):
        print(
            f"Line {count_line}: zone name '{name}' cannot contain a dash")
        sys.exit(1)


def parse_zone_line(kind: str, rest: str, count_line: int) -> Zone:
    """Parses a zone definition and builds its ``Zone`` object.

    The expected format is ``<name> <x> <y>`` optionally followed by a
    metadata block. The coordinates are converted to integers and the
    ``zone``, ``color`` and ``max_drones`` metadata are validated.

    Args:
        kind: Structural role of the zone (``start``, ``normal`` or
            ``end``), provided by the configuration directive.
        rest: Part of the line located after the directive key.
        count_line: Source line number.

    Returns:
        Fully validated and configured ``Zone`` object.

    Raises:
        ValueError: If the metadata contains an unknown key or if
            ``max_drones`` is not a positive integer.
        SystemExit: If the metadata block is malformed, if the line does
            not have exactly three fields, if the name is invalid, if the
            coordinates are not integers, or if the zone type or color is
            invalid. An error message is printed before exiting.
    """
    rest = rest.strip()
    bracket_idx = rest.find("[")
    if bracket_idx == -1:
        head, meta_raw = rest, ""
    else:
        if not rest.endswith("]"):
            print(
                f"Line {count_line}: malformed metadata block in '{rest}'")
            sys.exit(1)
        head, meta_raw = rest[:bracket_idx].strip(), rest[bracket_idx:]

    tokens = head.split()
    if len(tokens) != 3:
        print(
            f"Line {count_line}: expected '<name> <x> <y>', got '{head}'"
        )
        sys.exit(1)
    name, x_str, y_str = tokens
    _validate_name(name, count_line)

    try:
        x = int(x_str)
        y = int(y_str)
    except ValueError:
        print(
            f"Line {count_line}: coordinates must be integers,"
            f" got '{x_str} {y_str}'")
        sys.exit(1)

    metadata = parse_metadata(meta_raw, count_line)
    ensure_known_keys(metadata, {"zone", "color", "max_drones"}, count_line)

    zone_type = metadata.get("zone", "normal")
    if zone_type not in VALID_ZONE_TYPES:
        print(
            f"Line {count_line}: invalid zone type '{zone_type}', "
            f"must be one of {sorted(VALID_ZONE_TYPES)}"
        )
        sys.exit(1)

    color = metadata.get("color")
    if color is not None and (color == "" or any(c.isspace() for c in color)):
        print(
            f"Line {count_line}: "
            f"zone '{name}' missing required attribute 'color'"
        )
        sys.exit(1)

    max_drones = converted_to_integer(
        metadata.get(
            "max_drones",
            "1"),
        "max_drones",
        count_line)

    return Zone(
        name=name,
        x=x,
        y=y,
        kind=kind,
        zone_type=zone_type,
        color=color,
        max_drones=max_drones,
        count_line=count_line,
    )


class HubConfig:
    """Accumulates and validates the zones defined in the configuration.

    The class guarantees uniqueness of zone names and of ``(x, y)``
    coordinates, and separately tracks the start and end zones.

    Attributes:
        KIND_BY_KEY: Mapping from a directive key to the kind of zone it
            declares.
        zones: Dictionary of the zones registered so far, by name.
        start_name: Name of the start zone, or ``None`` if not declared.
        end_name: Name of the end zone, or ``None`` if not declared.
    """

    KIND_BY_KEY = {"start_hub": "start", "hub": "normal", "end_hub": "end"}

    def __init__(self) -> None:
        """Initializes an empty zone configuration."""
        self.zones: dict[str, Zone] = {}
        # To detect overlaps
        self._occupied_coords: dict[tuple[int, int], Zone] = {}
        self.start_name: str | None = None
        self.end_name: str | None = None

    def validate(self) -> None:
        """Checks that the file declares both a start and an end zone.

        Raises:
            ValueError: If no ``start_hub`` or no ``end_hub`` was declared.
        """
        if self.start_name is None:
            raise ValueError("No start_hub defined in the file.")
        if self.end_name is None:
            raise ValueError("No end_hub defined in the file.")

    def add_zone_entry(self, entry: OneLine) -> None:
        """Parses, validates and registers a zone declaration.

        The zone name and its ``(x, y)`` coordinates must be unique, and at
        most one start zone and one end zone may be declared.

        Args:
            entry: Configuration line containing a ``start_hub``, ``hub`` or
                ``end_hub`` directive.

        Raises:
            ValueError: If a second ``start_hub`` or ``end_hub`` is declared.
            SystemExit: If the line cannot be parsed, if the zone name is
                already used, or if the coordinates overlap with an existing
                zone. An error message is printed before exiting.
        """
        kind = self.KIND_BY_KEY[entry.key]

        # On laisse l'erreur de parsing remonter (sans try...except local si on
        # veut stopper le script)
        zone = parse_zone_line(kind, entry.value, entry.count_line)

        # 1. Validate name uniqueness
        if zone.name in self.zones:
            print(
                f"Line {entry.count_line}: duplicate zone name '{zone.name}' "
                f"(already defined line {self.zones[zone.name].count_line})"
            )
            sys.exit(1)

        # 2. Validate (x, y) coordinate overlap
        coords = (zone.x, zone.y)
        if coords in self._occupied_coords:
            existing_zone = self._occupied_coords[coords]
            print(
                f"Line {entry.count_line}: zone '{zone.name}' "
                "overlaps at coordinates "
                f"({zone.x}, {zone.y}) with existing zone "
                f"'{existing_zone.name}'"
                f"(defined line {existing_zone.count_line})"
            )
            sys.exit(1)

        # 3. Validate start uniqueness
        if kind == "start":
            if self.start_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: "
                    "multiple start_hub declarations "
                    "(first one line "
                    f"{self.zones[self.start_name].count_line})"
                )
            self.start_name = zone.name

        # 4. Validate end uniqueness
        if kind == "end":
            if self.end_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple end_hub declarations "
                    f"(first one line {self.zones[self.end_name].count_line})"
                )
            self.end_name = zone.name

        # Register the zone and its coordinates
        self.zones[zone.name] = zone
        self._occupied_coords[coords] = zone


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
