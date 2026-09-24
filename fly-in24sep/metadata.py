"""Helpers to parse and validate ``[key=value ...]`` metadata blocks.

Also provides a strict conversion of text values into positive
integers, shared by the zone, connection and drone-count parsers.
"""

import sys


def parse_metadata(raw: str, line_no: int) -> dict[str, str]:
    """Parses a metadata block in the ``[key=value ...]`` format.

    Metadata items are separated by spaces. Each item must contain an
    ``=`` sign and keys must be unique. An empty string, or an empty
    pair of brackets, produces an empty dictionary.

    Args:
        raw: Raw text of the metadata block.
        line_no: Line number used to produce precise error messages.

    Returns:
        Dictionary mapping each metadata key to its text value.

    Raises:
        SystemExit: If the block is not enclosed in brackets, if a token
            has no ``=``, if a key or a value is empty, or if a key is
            duplicated. An error message is printed before exiting.
    """
    raw = raw.strip()
    if raw == "":
        return {}
    if not (raw.startswith("[") and raw.endswith("]")):
        print(
            f"Line {line_no}: metadata must be enclosed in [...], got '{raw}'"
        )
        sys.exit(1)
    inner = raw[1:-1].strip()
    if inner == "":
        return {}

    metadata: dict[str, str] = {}
    for token in inner.split():
        if "=" not in token:
            print(
                f"Line {line_no}: invalid metadata token '{token}' "
                "(expected key=value)"
            )
            sys.exit(1)
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "" or value == "":
            print(
                f"Line {line_no}: invalid metadata token '{token}'"
            )
            sys.exit(1)
        if key in metadata:
            print(
                f"Line {line_no}: duplicate metadata key '{key}'"
            )
            sys.exit(1)
        metadata[key] = value
    return metadata


def ensure_known_keys(
    metadata: dict[str, str], allowed: set[str],
    line_no: int
) -> None:
    """Checks that all metadata keys are allowed.

    Unknown keys are sorted to produce a stable, easy-to-read error
    message.

    Args:
        metadata: Dictionary of metadata to check.
        allowed: Set of allowed keys.
        line_no: Line number associated with the metadata.

    Raises:
        ValueError: If one or more keys are not part of ``allowed``.
    """
    unknown = sorted(set(metadata) - allowed)
    if unknown:
        raise ValueError(
            f"Line {line_no}: unknown metadata key(s) {unknown}, "
            f"allowed: {sorted(allowed)}"
        )


def converted_to_integer(value_str: str, key: str, count_line: int) -> int:
    """Converts a text value into a strictly positive integer.

    This function centralizes the validation of positive numeric
    configuration parameters and produces an error message indicating
    the relevant line and key.

    Args:
        value_str: Text value to convert.
        key: Name of the parameter concerned.
        count_line: Line number in the configuration file.

    Returns:
        Integer strictly greater than zero.

    Raises:
        ValueError: If the value is not an integer or if it is less
            than or equal to zero.
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
