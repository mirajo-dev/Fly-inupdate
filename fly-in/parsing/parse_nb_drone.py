import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from .read_config import ReadFile, OneLine
from .metadata import converted_to_integer
from dataclasses import dataclass


@dataclass
class Drone:
    id_drone: str
    current_zone: str
    goal_zone: str


class DroneConfig:
    def __init__(self, data: list[OneLine]):
        self._value = 0
        self._extract_value(data)

    def _extract_value(self, data: list[OneLine]) -> None:
        if not data:
            raise ValueError("DroneConfig error: empty configuration")
        first = data[0]
        if first.key != "nb_drones":
            raise ValueError(
                f"Line {first.count_line}: file must start with"
                f"'nb_drones: <number>', got '{first.key}'"
            )
            
        occurances = [occ for occ in data if occ.key == "nb_drones"]
        if len(occurances) > 1:
            raise ValueError(
                f"Line {occurances[1].count_line}: 'nb_drones' declared more than once"
            )
        
        self._value = converted_to_integer(first.value, "nb_drones", first.count_line)
        
    def get_nb_drone(self) -> int:
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
