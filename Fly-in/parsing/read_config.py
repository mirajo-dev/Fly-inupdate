from dataclasses import dataclass
import sys


@dataclass
class OneLine:
    count_line: int
    key: str
    value: str


@dataclass
class ReadFile:
    @staticmethod
    def read_config(filename: str) -> list[OneLine]:
        try:
            with open(filename, "r") as file:
                line = file.readlines()
        except Exception as e:
            print(e)
        list_lines: list[OneLine] = []
        for count_line, strings in enumerate(line, start=1):
            strings = strings.strip()
            if strings == "" or strings.startswith("#"):
                continue
            if ":" not in strings:
                raise ValueError(f"Line: {count_line}: missing ':' in {strings}")
            key, value = strings.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key == "":
                raise ValueError(f"Line {count_line}: missing key before ':'")
            list_lines.append(OneLine(count_line, key, value))
            if not list_lines:
                raise ValueError(f"'{filename}': file is empty or has no content")
        return list_lines
            
            
            
if __name__ == "__main__":
    try:
        config = ReadFile.read_config(sys.argv[1])
        print(config)
    except Exception as e:
        print(e)
