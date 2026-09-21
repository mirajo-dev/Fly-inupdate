from dataclasses import dataclass
import sys


@dataclass
class OneLine:
    """Représente une directive non interprétée issue
    d'une ligne de configuration.

Attributes:
    count_line: Numéro de ligne dans le fichier source.
    key: Nom de la directive située avant ``:``.
    value: Contenu textuel situé après ``:``.
"""
    count_line: int
    key: str
    value: str


@dataclass
class ReadFile:
    """Fournit la lecture et le découpage initial des
    fichiers de configuration.

La classe transforme chaque directive utile en objet ``OneLine`` et ignore les
lignes vides ainsi que les commentaires commençant par ``#``.
"""
    @staticmethod
    def read_config(filename: str) -> list[OneLine]:
        """Lit un fichier de configuration et le transforme en ``OneLine``.

Chaque ligne non vide et non commentée doit contenir ``:``.
La partie gauche est
utilisée comme clé et la partie droite comme valeur,
après suppression des espaces
superflus.

Args:
    filename: Chemin du fichier à lire.

Returns:
    Liste des objets ``OneLine`` correspondant aux directives valides.

Raises:
    ValueError: Si une ligne active ne contient pas ``:``,
    si sa clé est vide ou
        si une autre erreur de validation de format est rencontrée.
    OSError: Peut être rencontré lors de l'ouverture du fichier ;
    l'implémentation
        actuelle l'affiche mais ne le relance pas explicitement.
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
                raise ValueError(f"Line {count_line}: missing key before ':'")
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
