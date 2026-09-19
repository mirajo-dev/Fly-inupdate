def parse_metadata(raw: str, line_no: int) -> dict[str, str]:
    """Analyse un bloc de métadonnées au format ``[key=value ...]``.

Les métadonnées sont séparées par des espaces. Chaque élément doit contenir un
signe ``=`` et les clés doivent être uniques. Une chaîne vide ou l'absence de bloc
produit un dictionnaire vide.

Args:
    raw: Texte brut du bloc de métadonnées.
    line_no: Numéro de ligne utilisé pour produire des messages d'erreur précis.

Returns:
    Dictionnaire associant chaque clé de métadonnée à sa valeur textuelle.

Raises:
    ValueError: Si le bloc n'est pas correctement délimité, contient un token
        invalide, une clé ou valeur vide, ou une clé dupliquée.
"""
    raw = raw.strip()
    if raw == "":
        return {}
    if not (raw.startswith("[") and raw.endswith("]")):
        raise ValueError(
            f"Line {line_no}: metadata must be enclosed in [...], got '{raw}'"
        )
    inner = raw[1:-1].strip()
    if inner == "":
        return {}

    metadata: dict[str, str] = {}
    for token in inner.split():
        if "=" not in token:
            raise ValueError(
                f"Line {line_no}: invalid metadata token '{token}' "
                "(expected key=value)"
            )
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "" or value == "":
            raise ValueError(f"Line {line_no}: invalid metadata token '{token}'")
        if key in metadata:
            raise ValueError(f"Line {line_no}: duplicate metadata key '{key}'")
        metadata[key] = value
    return metadata


def ensure_known_keys(metadata: dict[str, str], allowed: set[str], line_no: int) -> None:
    """Vérifie que toutes les clés de métadonnées sont autorisées.

Les clés inconnues sont triées afin de produire un message d'erreur stable et
facile à lire.

Args:
    metadata: Dictionnaire de métadonnées à vérifier.
    allowed: Ensemble des clés autorisées.
    line_no: Numéro de ligne associé aux métadonnées.

Returns:
    ``None`` si toutes les clés sont autorisées.

Raises:
    ValueError: Si une ou plusieurs clés ne font pas partie de ``allowed``.
"""
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise ValueError(
            f"Line {line_no}: unknown metadata key(s) {unknown}, "
            f"allowed: {sorted(allowed)}"
        )


def converted_to_integer(value_str: str, key: str, count_line: int) -> int:
    """Convertit une valeur textuelle en entier strictement positif.

Cette fonction centralise la validation des paramètres numériques positifs de la
configuration et produit une erreur indiquant la ligne et la clé concernées.

Args:
    value_str: Valeur textuelle à convertir.
    key: Nom du paramètre concerné.
    count_line: Numéro de ligne dans le fichier de configuration.

Returns:
    Entier strictement supérieur à zéro.

Raises:
    ValueError: Si la valeur n'est pas un entier ou si elle est inférieure ou égale
        à zéro.
"""
    try:
        value = int(value_str)
    except ValueError:
        raise ValueError(
            f"Line {count_line}: {key} must be a positive integer, "
            f"got '{value_str}"
        )
    if value <= 0:
        raise ValueError(
            f"Line {count_line}: {key} must be a positive integer, got {value}"
        )
    return value
