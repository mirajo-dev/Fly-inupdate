def parse_metadata(raw: str, line_no: int) -> dict[str, str]:
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
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise ValueError(
            f"Line {line_no}: unknown metadata key(s) {unknown}, "
            f"allowed: {sorted(allowed)}"
        )


def converted_to_integer(value_str: str, key: str, count_line: int) -> int:
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
