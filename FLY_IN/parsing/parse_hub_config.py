from .metadata import parse_metadata, ensure_known_keys, converted_to_integer
from .read_config import ReadFile, OneLine
import sys
import os
from dataclasses import dataclass


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
FORBIDDEN_NAME_CHARS = {"-"}


@dataclass
class Zone:
    """Décrit une zone du réseau et ses contraintes de capacité.

Attributes:
    name: Nom unique de la zone.
    x: Coordonnée horizontale dans la carte.
    y: Coordonnée verticale dans la carte.
    kind: Rôle structurel de la zone, par exemple
    ``start``, ``normal`` ou ``end``.
    zone_type: Type fonctionnel de la zone
    (normal, blocked, restricted ou priority).
    color: Couleur facultative utilisée pour le rendu graphique.
    max_drones: Nombre maximal de drones pouvant occuper la zone.
    count_line: Numéro de ligne de configuration ayant défini la zone.
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
    """Valide le nom d'une zone selon les contraintes du format.

Un nom doit être non vide, ne contenir aucun espace et
ne pas contenir de tiret.
Ces règles évitent notamment les ambiguïtés avec la syntaxe des connexions.

Args:
    name: Nom de zone à vérifier.
    count_line: Numéro de ligne utilisé dans les erreurs.

Returns:
    ``None`` si le nom est valide.

Raises:
    ValueError: Si le nom est vide, contient un espace ou contient un tiret.
"""
    if name == "":
        raise ValueError(f"Line {count_line}: zone name is empty")
    if any(c.isspace() for c in name):
        raise ValueError(
            f"Line {count_line}: zone name '{name}' cannot contain spaces")
    if any(c in FORBIDDEN_NAME_CHARS for c in name):
        raise ValueError(
            f"Line {count_line}: zone name '{name}' cannot contain a dash")


def parse_zone_line(kind: str, rest: str, count_line: int) -> Zone:
    """Analyse la définition d'une zone et construit son objet ``Zone``.

Le format attendu est ``<name> <x> <y>`` éventuellement suivi d'un bloc de
métadonnées. Les coordonnées sont converties en entiers et les métadonnées
``zone``, ``color`` et ``max_drones`` sont validées.

Args:
    kind: Rôle structurel de la zone, fourni par la directive de configuration.
    rest: Partie de la ligne située après la clé de directive.
    count_line: Numéro de ligne source.

Returns:
    Objet ``Zone`` entièrement validé et configuré.

Raises:
    ValueError: Si le format, le nom, les coordonnées ou les métadonnées sont
        invalides.
"""
    rest = rest.strip()
    bracket_idx = rest.find("[")
    if bracket_idx == -1:
        head, meta_raw = rest, ""
    else:
        if not rest.endswith("]"):
            raise ValueError(
                f"Line {count_line}: malformed metadata block in '{rest}'")
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
            f"Line {count_line}: coordinates must be integers,"
            f" got '{x_str} {y_str}'")

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
    """Accumule et valide les zones définies dans la configuration.

    La classe garantit l'unicité des noms de zones,
    l'unicité des coordonnées (x, y)
    et mémorise séparément les zones de départ et d'arrivée.
    """
    KIND_BY_KEY = {"start_hub": "start", "hub": "normal", "end_hub": "end"}

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        # Pour détecter les chevauchements
        self._occupied_coords: dict[tuple[int, int], Zone] = {}
        self.start_name: str | None = None
        self.end_name: str | None = None

    def validate(self) -> None:
        """Vérifie que le fichier contient au moins un point
        de départ et d'arrivée."""
        if self.start_name is None:
            raise ValueError("No start_hub defined in the file.")
        if self.end_name is None:
            raise ValueError("No end_hub defined in the file.")

    def add_zone_entry(self, entry: OneLine) -> None:
        kind = self.KIND_BY_KEY[entry.key]

        # On laisse l'erreur de parsing remonter (sans try...except local si on
        # veut stopper le script)
        zone = parse_zone_line(kind, entry.value, entry.count_line)

        # 1. Validation de l'unicité du nom
        if zone.name in self.zones:
            print(
                f"Line {entry.count_line}: duplicate zone name '{zone.name}' "
                f"(already defined line {self.zones[zone.name].count_line})"
            )
            sys.exit(1)

        # 2. Validation du chevauchement de coordonnées (x, y)
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

        # 3. Validation de l'unicité du start
        if kind == "start":
            if self.start_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: "
                    "multiple start_hub declarations "
                    "(first one line "
                    f"{self.zones[self.start_name].count_line})"
                )
            self.start_name = zone.name

        # 4. Validation de l'unicité du end
        if kind == "end":
            if self.end_name is not None:
                raise ValueError(
                    f"Line {entry.count_line}: multiple end_hub declarations "
                    f"(first one line {self.zones[self.end_name].count_line})"
                )
            self.end_name = zone.name

        # Enregistrement de la zone et de ses coordonnées
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
