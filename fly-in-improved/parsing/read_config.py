from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OneLine:
    """A parsed non-empty input line."""

    count_line: int
    key: str
    value: str


class ReadFile:
    """Read and normalize map configuration files."""

    @staticmethod
    def read_config(filename: str) -> list[OneLine]:
        """Return directives from a map file with line numbers."""
        try:
            with open(filename, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except OSError as exc:
            raise OSError(f"Cannot read '{filename}': {exc}") from exc

        entries: list[OneLine] = []
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(
                    f"Line {line_no}: missing ':' in '{line}'"
                )

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                raise ValueError(f"Line {line_no}: missing key before ':'")
            entries.append(OneLine(line_no, key, value))

        if not entries:
            raise ValueError(f"'{filename}': file is empty or has no content")
        return entries
