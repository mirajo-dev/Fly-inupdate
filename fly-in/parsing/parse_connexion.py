import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .read_config import ReadFile, OneLine
from .metadata import parse_metadata, ensure_known_keys, converted_to_integer
from .parse_hub_config import Zone, HubConfig


@dataclass
class Connection:
    """Représente une connexion non orientée entre deux zones.

Attributes:
    zone_a: Nom de la première extrémité.
    zone_b: Nom de la seconde extrémité.
    max_link_capacity: Nombre maximal de drones pouvant emprunter la connexion
        pendant un tour.
    count_line: Numéro de ligne ayant défini la connexion.
"""
    zone_a: str
    zone_b: str
    max_link_capacity: int = 1
    count_line: int = 0

    def get_zones(self) -> tuple[str, str]:
        """Retourne les deux extrémités de la connexion dans leur ordre déclaré.

Returns:
    Tuple ``(zone_a, zone_b)`` contenant les noms des deux zones.
"""
        return self.zone_a, self.zone_b

    def get_key(self) -> str:
        """Construit une clé textuelle identifiant la connexion.

Returns:
    Chaîne de la forme ``Connection:zone_a-zone_b``.
"""
        return f"Connection:{self.zone_a}-{self.zone_b}"


def parse_connection_line(rest: str, count_line: int) -> Connection:
    """Analyse une définition de connexion et crée un objet ``Connection``.

Le format de base est ``<zone1>-<zone2>`` avec un bloc optionnel de métadonnées.
La méthode refuse les connexions vers soi-même et valide la capacité
``max_link_capacity``.

Args:
    rest: Partie de la ligne située après la directive ``connection``.
    count_line: Numéro de ligne source.

Returns:
    Objet ``Connection`` validé.

Raises:
    ValueError: Si le format de connexion ou ses métadonnées sont invalides, si
        les deux extrémités sont identiques ou si la capacité n'est pas positive.
"""
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

    """Gère les connexions définies entre les zones du réseau.

La configuration conserve la liste des connexions et un ensemble de clés
normalisées permettant de détecter les doublons indépendamment de l'ordre des
extrémités.

Attributes:
    _zones: Dictionnaire des zones connues, utilisé pour vérifier les références.
    connections: Liste des connexions valides.
    _seen: Dictionnaire des connexions déjà rencontrées avec leur ligne source.
"""
    def __init__(self, zones: dict[str, Zone]) -> None:
        """Initialise une configuration de connexions.

Args:
    zones: Dictionnaire des zones déjà déclarées. Les connexions doivent référencer
        exclusivement ces zones.
"""
        self._zones = zones
        self.connections: list[Connection] = []
        self._seen: dict[frozenset, int] = {}

    def add_connection_entry(self, entry: OneLine) -> None:
        """Analyse, valide et ajoute une connexion.

Chaque extrémité doit exister dans le dictionnaire des zones. Une clé ``frozenset``
est utilisée pour détecter les doublons sans tenir compte de l'ordre
``zone_a-zone_b`` ou ``zone_b-zone_a``.

Args:
    entry: Ligne de configuration contenant la directive de connexion.

Returns:
    ``None``. La connexion valide est ajoutée à ``connections``.

Raises:
    ValueError: Si une zone référencée n'existe pas ou si la connexion a déjà été
        déclarée.
"""
        try:
            conn = parse_connection_line(entry.value, entry.count_line)
        except ValueError as e:
            print(f"Error :{e}")
            sys.exit(1)

        for name in (conn.zone_a, conn.zone_b):
            if name not in self._zones:
                print(
                    f"Line {entry.count_line}: connection references undefined "
                    f"(or not-yet-defined) zone '{name}'"
                )
                sys.exit(1)

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
