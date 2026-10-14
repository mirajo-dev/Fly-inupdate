"""Parsing and validation of ``start_hub``, ``hub`` and ``end_hub`` lines.

Defines the ``Zone`` dataclass, the line parser ``parse_zone_line``
and the ``HubConfig`` accumulator. Running the module directly prints
the parsed zones.
"""

from metadata import parse_metadata, ensure_known_keys, converted_to_integer
from read_config import OneLine
import sys
import os
from dataclasses import dataclass


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
FORBIDDEN_NAME_CHARS = {"-"}
ZONE_KINDS: dict[str, str] = {
    "start_hub": "start",
    "hub": "normal",
    "end_hub": "end",
}
DEFAULT_ZONE_TYPE = "normal"
DEFAULT_MAX_DRONES = "1"


@dataclass
class Zone:
    """Describe a network zone and its capacity constraints.

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
    zone_type: str = DEFAULT_ZONE_TYPE
    color: str | None = None
    max_drones: int = int(DEFAULT_MAX_DRONES)
    count_line: int = 0


def _check_prefix(key: str, count_line: int) -> str:
    """Check the directive key of a zone line and return the zone kind.

    Args:
        key: Directive key found before the colon.
        count_line: Line number used in error messages.

    Returns:
        Structural role of the zone: ``start``, ``normal`` or ``end``.

    Raises:
        SystemExit: If the key is not ``start_hub``, ``hub`` or
            ``end_hub``. An error message is printed before exiting.
    """
    if key not in ZONE_KINDS:
        print(
            f"Line {count_line}: unknown directive '{key}', "
            f"must be one of {sorted(ZONE_KINDS)}")
        sys.exit(1)
    return ZONE_KINDS[key]


def _validate_name(name: str, count_line: int) -> None:
    """Validate a zone name against the format's constraints.

    Every character is accepted except the dash, which would be
    ambiguous with the ``<zone1>-<zone2>`` connection syntax. Brackets
    are refused too, because they belong to the metadata block.

    Args:
        name: Zone name to check.
        count_line: Line number used in error messages.

    Raises:
        SystemExit: If the name contains a dash or a bracket. An error
            message is printed before exiting.
    """
    if any(c in FORBIDDEN_NAME_CHARS for c in name):
        print(
            f"Line {count_line}: zone name '{name}' cannot contain a dash")
        sys.exit(1)
    if "[" in name or "]" in name:
        print(
            f"Line {count_line}: zone name '{name}' cannot contain a "
            "bracket (metadata must come after the coordinates)")
        sys.exit(1)


def _parse_coordinates(
        x_str: str, y_str: str, count_line: int) -> tuple[int, int]:
    """Convert the two coordinate fields to integers.

    Args:
        x_str: Text of the horizontal coordinate.
        y_str: Text of the vertical coordinate.
        count_line: Line number used in error messages.

    Returns:
        Tuple ``(x, y)``.

    Raises:
        SystemExit: If a bracket is glued to a coordinate or if a
            coordinate is not an integer. An error message is printed
            before exiting.
    """
    for field in (x_str, y_str):
        if "[" in field or "]" in field:
            print(
                f"Line {count_line}: a space is required before '[' "
                f"(got '{field}')")
            sys.exit(1)
    try:
        return int(x_str), int(y_str)
    except ValueError:
        print(
            f"Line {count_line}: coordinates must be integers,"
            f" got '{x_str} {y_str}'")
        sys.exit(1)


def _parse_optional_metadata(
        extra_tokens: list[str], count_line: int) -> dict[str, str]:
    """Parse the optional metadata tokens found after the coordinates.

    Args:
        extra_tokens: Tokens of the line located after ``<name> <x> <y>``.
        count_line: Line number used in error messages.

    Returns:
        Dictionary of metadata, empty if the line has none.

    Raises:
        SystemExit: If the brackets are not a single ``[...]`` block. An
            error message is printed before exiting.
    """
    if not extra_tokens:
        return {}
    raw = " ".join(extra_tokens)
    if raw.count("[") != 1 or raw.count("]") != 1:
        print(
            f"Line {count_line}: metadata must be enclosed in a single "
            f"[...], got '{raw}'")
        sys.exit(1)
    return parse_metadata(raw, count_line)


def parse_zone_line(key: str, rest: str, count_line: int) -> Zone:
    """Parse a zone definition and build its ``Zone`` object.

    The line is processed by splitting it into tokens, in this order:
    the directive key, the zone name, the two coordinates and, if
    present, the metadata block. Missing metadata fall back to the
    defaults ``zone=normal``, no color and ``max_drones=1``.

    Args:
        key: Directive key (``start_hub``, ``hub`` or ``end_hub``).
        rest: Part of the line located after the directive key.
        count_line: Source line number.

    Returns:
        Fully validated and configured ``Zone`` object.

    Raises:
        ValueError: If the metadata contains an unknown key or if
            ``max_drones`` is not a positive integer.
        SystemExit: If the directive is unknown, if the line has fewer
            than three fields, if the name is invalid, if the
            coordinates are not integers, if the metadata block is
            malformed, or if the zone type is invalid. An error message
            is printed before exiting.
    """
    kind = _check_prefix(key, count_line)

    tokens = rest.split()
    if len(tokens) < 3:
        print(
            f"Line {count_line}: expected '<name> <x> <y> [metadata]', "
            f"got '{rest.strip()}'")
        sys.exit(1)
    name = tokens[0]
    _validate_name(name, count_line)

    x, y = _parse_coordinates(tokens[1], tokens[2], count_line)

    metadata = _parse_optional_metadata(tokens[3:], count_line)
    ensure_known_keys(metadata, {"zone", "color", "max_drones"}, count_line)

    zone_type = metadata.get("zone", DEFAULT_ZONE_TYPE)
    if zone_type not in VALID_ZONE_TYPES:
        print(
            f"Line {count_line}: invalid zone type '{zone_type}', "
            f"must be one of {sorted(VALID_ZONE_TYPES)}"
        )
        sys.exit(1)

    max_drones = converted_to_integer(
        metadata.get("max_drones", DEFAULT_MAX_DRONES),
        "max_drones",
        count_line)

    return Zone(
        name=name,
        x=x,
        y=y,
        kind=kind,
        zone_type=zone_type,
        color=metadata.get("color"),
        max_drones=max_drones,
        count_line=count_line,
    )


class HubConfig:
    """Accumulate and validate the zones defined in the configuration.

    The class guarantees uniqueness of zone names and of ``(x, y)``
    coordinates, and separately tracks the start and end zones.

    Attributes:
        KIND_BY_KEY: Mapping from a directive key to the kind of zone it
            declares.
        zones: Dictionary of the zones registered so far, by name.
        start_name: Name of the start zone, or ``None`` if not declared.
        end_name: Name of the end zone, or ``None`` if not declared.
    """

    KIND_BY_KEY = ZONE_KINDS

    def __init__(self) -> None:
        """Initialize an empty zone configuration."""
        self.zones: dict[str, Zone] = {}
        self._occupied_coords: dict[tuple[int, int], Zone] = {}
        self.start_name: str | None = None
        self.end_name: str | None = None

    def validate(self) -> None:
        """Check that the file declares both a start and an end zone.

        Raises:
            ValueError: If no ``start_hub`` or no ``end_hub`` was declared.
        """
        if self.start_name is None:
            raise ValueError("No start_hub defined in the file.")
        if self.end_name is None:
            raise ValueError("No end_hub defined in the file.")

    def add_zone_entry(self, entry: OneLine) -> None:
        """Parse, validate and register a zone declaration.

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
        zone = parse_zone_line(entry.key, entry.value, entry.count_line)
        kind = zone.kind

        if zone.name in self.zones:
            print(
                f"Line {entry.count_line}: duplicate zone name '{zone.name}' "
                f"(already defined line {self.zones[zone.name].count_line})"
            )
            sys.exit(1)

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

        if kind == "start":
            if self.start_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: "
                    "multiple start_hub declarations "
                    "(first one line "
                    f"{self.zones[self.start_name].count_line})"
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
        self._occupied_coords[coords] = zone
