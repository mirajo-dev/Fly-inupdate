"""Reading and first-level splitting of Fly-in configuration files.

Each usable line of the form ``key: value`` becomes a ``OneLine``
object; interpreting the values is left to the specialized parsers.
"""

from dataclasses import dataclass
import sys


@dataclass
class OneLine:
    """Represents a raw, uninterpreted directive from a configuration line.

    Attributes:
        count_line: Line number in the source file.
        key: Directive name located before ``:``.
        value: Text content located after ``:``.
    """

    count_line: int
    key: str
    value: str


@dataclass
class ReadFile:
    """Provides reading and initial splitting of configuration files.

    The class turns each usable directive into a ``OneLine`` object and
    ignores blank lines as well as comments starting with ``#``.
    """

    @staticmethod
    def read_config(filename: str) -> list[OneLine]:
        """Reads a configuration file and turns it into ``OneLine`` objects.

        Each non-empty, non-commented line must contain ``:``. The left part
        is used as the key and the right part as the value, after stripping
        surrounding whitespace.

        Args:
            filename: Path of the file to read.

        Returns:
            List of ``OneLine`` objects corresponding to the valid
            directives, in file order.

        Raises:
            SystemExit: If the file cannot be read, if an active line does
                not contain ``:``, or if its key is empty. An error message
                is printed before exiting.
        """
        try:
            with open(filename, "r") as file:
                line = file.readlines()
        except Exception as e:
            print(e)
            sys.exit(1)
        list_lines: list[OneLine] = []
        for count_line, strings in enumerate(line, start=1):
            strings = strings.strip()
            if strings == "" or strings.startswith("#"):
                continue
            if ":" not in strings:
                print(f"Line: {count_line}: missing ':' in {strings}")
                sys.exit(1)
            key, value = strings.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "":
                print(f"Line {count_line}: missing key before ':'")
                sys.exit(1)
            list_lines.append(OneLine(count_line, key, value))
            if not list_lines:
                raise ValueError(
                    f"'{filename}': file is empty or has no content")
        return list_lines


if __name__ == "__main__":
    try:
        config = ReadFile.read_config(sys.argv[1])
        print(config)
    except Exception as e:
        print(e)
