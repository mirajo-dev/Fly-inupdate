from __future__ import annotations

from pathlib import Path

from parsing.network import NetworkParser


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "parsing" / "maps"


def test_all_reference_maps_parse() -> None:
    """All provided maps should pass the parser."""
    maps = list(MAPS.rglob("*.txt"))
    assert maps
    for map_file in maps:
        network = NetworkParser(str(map_file)).parse()
        assert network.nb_drones > 0
        assert network.start in network.zones
        assert network.end in network.zones
        assert network.connections


def test_linear_map() -> None:
    """The easy linear map has four zones and two drones."""
    path = MAPS / "easy" / "01_linear_path.txt"
    network = NetworkParser(str(path)).parse()
    assert network.nb_drones == 2
    assert len(network.zones) == 4
