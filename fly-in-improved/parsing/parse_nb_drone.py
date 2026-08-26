from __future__ import annotations

from parsing.metadata import converted_to_integer
from parsing.read_config import OneLine


class DroneConfig:
    """Validate and store the number of drones."""

    def __init__(self, data: list[OneLine]) -> None:
        if not data:
            raise ValueError("DroneConfig error: empty configuration")
        first = data[0]
        if first.key != "nb_drones":
            raise ValueError(
                f"Line {first.count_line}: file must start with "
                "'nb_drones: <number>'"
            )

        occurrences = [entry for entry in data if entry.key == "nb_drones"]
        if len(occurrences) > 1:
            raise ValueError(
                f"Line {occurrences[1].count_line}: "
                "'nb_drones' declared more than once"
            )

        self._value = converted_to_integer(
            first.value, "nb_drones", first.count_line
        )

    def get_nb_drone(self) -> int:
        """Return the configured drone count."""
        return self._value
