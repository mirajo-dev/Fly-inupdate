from dataclasses import dataclass
from .metadata import converted_to_integer
from .read_config import ReadFile, OneLine
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class Drone:
    """Représente l'état logique d'un drone dans la simulation.

Attributes:
    id_drone: Identifiant unique du drone, par exemple ``D1``.
    current_zone: Nom de la zone où le drone se trouve actuellement.
    goal_zone: Nom de la zone que le drone doit atteindre.
"""
    id_drone: str
    current_zone: str
    goal_zone: str


class DroneConfig:
    """Stocke et valide le nombre de drones déclaré dans la configuration.

La classe attend que la première directive soit ``nb_drones`` et
garantit qu'elle
n'est déclarée qu'une seule fois. La valeur est convertie en entier strictement
positif.

Attributes:
    _value: Nombre de drones extrait de la configuration.
"""

    def __init__(self, data: list[OneLine]):
        """Initialise la configuration du nombre de drones.

Args:
    data: Lignes de configuration déjà parsées.

Raises:
    ValueError: Si la configuration est vide, si la première ligne n'est pas
        ``nb_drones`` ou si la valeur n'est pas un entier positif.
"""
        self._value = 0
        self._extract_value(data)

    def _extract_value(self, data: list[OneLine]) -> None:
        """Extrait, valide et mémorise le nombre de drones.

La première ligne doit obligatoirement déclarer ``nb_drones`` et
cette directive
ne peut apparaître qu'une seule fois. La valeur est ensuite convertie en entier
positif avec ``converted_to_integer()``.

Args:
    data: Liste des lignes de configuration parsées.

Returns:
    ``None``. La valeur est enregistrée dans ``self._value``.

Raises:
    ValueError: Si les données sont absentes, mal ordonnées, dupliquées ou
        contiennent un nombre invalide.
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
        """Retourne le nombre de drones configuré.

Returns:
    Nombre de drones sous forme d'entier strictement positif.
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
