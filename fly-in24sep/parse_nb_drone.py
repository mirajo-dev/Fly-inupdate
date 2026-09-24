"""Parsing and validation of the ``nb_drones`` directive.

Also defines the ``Drone`` dataclass describing the logical state of
a drone. Running the module directly prints the parsed drone count.
"""

from dataclasses import dataclass
from metadata import converted_to_integer
from read_config import ReadFile, OneLine
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Drone:
    """Represents the logical state of a drone in the simulation.

    Attributes:
        id_drone: Unique identifier of the drone, e.g. ``D1``.
        current_zone: Name of the zone the drone is currently in.
        goal_zone: Name of the zone the drone must reach.
    """

    id_drone: str
    current_zone: str
    goal_zone: str


class DroneConfig:
    """Stores and validates the number of drones declared in the config.

    The class expects the first directive to be ``nb_drones`` and
    guarantees that it is declared only once. The value is converted
    into a strictly positive integer.

    Attributes:
        _value: Number of drones extracted from the configuration.
    """

    def __init__(self, data: list[OneLine]) -> None:
        """Initializes the drone-count configuration.

        Args:
            data: Already-parsed configuration lines.

        Raises:
            ValueError: If the configuration is empty, if ``nb_drones`` is
                declared more than once, or if its value is not a positive
                integer.
            SystemExit: If the first directive is not ``nb_drones``. An
                error message is printed before exiting.
        """
        self._value = 0
        self._extract_value(data)

    def _extract_value(self, data: list[OneLine]) -> None:
        """Extracts, validates and stores the number of drones.

        The first line must declare ``nb_drones``, and this directive may
        only appear once. The value is then converted into a positive
        integer with ``converted_to_integer()`` and stored in
        ``self._value``.

        Args:
            data: List of parsed configuration lines.

        Raises:
            ValueError: If the data is empty, if ``nb_drones`` is declared
                more than once, or if its value is not a positive integer.
            SystemExit: If the first directive is not ``nb_drones``. An
                error message is printed before exiting.
        """
        if not data:
            raise ValueError("DroneConfig error: empty configuration")
        first = data[0]
        if first.key != "nb_drones":
            print(
                f"Line {first.count_line}: file must start with"
                f"'nb_drones: <number>', got '{first.key}'"
            )
            sys.exit(1)

        occurances = [occ for occ in data if occ.key == "nb_drones"]
        if len(occurances) > 1:
            raise ValueError(
                f"Line {occurances[1].count_line}: "
                f"'nb_drones' declared more than once")

        self._value = converted_to_integer(
            first.value, "nb_drones", first.count_line)

    def get_nb_drone(self) -> int:
        """Returns the configured number of drones.

        Returns:
            Number of drones as a strictly positive integer.
        """
        return self._value


if __name__ == "__main__":

    try:
        file = ReadFile
        # print(file.read_config(sys.argv[1]))
        data = file.read_config(sys.argv[1])
        drone_conf = DroneConfig(data)

        print(f"Number Drones: {drone_conf.get_nb_drone()}")
    except Exception as e:
        print(e)
