from __future__ import annotations


def parse_metadata(raw: str, line_no: int) -> dict[str, str]:
    """Parse a single [...] metadata block."""
    raw = raw.strip()
    if not raw:
        return {}
    if not (raw.startswith("[") and raw.endswith("]")):
        raise ValueError(
            f"Line {line_no}: metadata must be enclosed in [...]"
        )

    inner = raw[1:-1].strip()
    if not inner:
        return {}

    metadata: dict[str, str] = {}
    for token in inner.split():
        if "=" not in token:
            raise ValueError(
                f"Line {line_no}: invalid metadata token '{token}'"
            )
        key, value = token.split("=", 1)
        if not key or not value:
            raise ValueError(
                f"Line {line_no}: invalid metadata token '{token}'"
            )
        if key in metadata:
            raise ValueError(
                f"Line {line_no}: duplicate metadata key '{key}'"
            )
        metadata[key] = value
    return metadata


def ensure_known_keys(
    metadata: dict[str, str],
    allowed: set[str],
    line_no: int,
) -> None:
    """Reject metadata keys not supported by the project."""
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise ValueError(
            f"Line {line_no}: unknown metadata key(s) {unknown}; "
            f"allowed: {sorted(allowed)}"
        )


def converted_to_integer(value_str: str, key: str, line_no: int) -> int:
    """Convert a strictly positive integer field."""
    try:
        value = int(value_str)
    except ValueError as exc:
        raise ValueError(
            f"Line {line_no}: {key} must be a positive integer, got '{value_str}'"
        ) from exc
    if value <= 0:
        raise ValueError(
            f"Line {line_no}: {key} must be a positive integer, got {value}"
        )
    return value
