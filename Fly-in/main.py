from display import Graphe
from parsing.network import NetworkParser
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 main.py")
        sys.exit(1)
    network = NetworkParser(sys.argv[1]).parse()
    game = Graphe(network)
    game.running()