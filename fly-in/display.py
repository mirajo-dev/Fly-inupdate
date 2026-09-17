from collections import deque
import argparse
import sys

from parsing.network import Network, NetworkParser
from parsing.parse_hub_config import Zone
from parsing.parse_nb_drone import Drone, DroneConfig
from parsing.parse_connexion import Connection
from camera import Camera
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
try:
    import pygame
    from pygame import Color, Surface, Vector2
except ImportError:
    print("[Error] Missing 'pygame' module. Required installation: 'pip install pygame'")
    sys.exit(1)
from algo_A_star import find_all_paths

BG_COLOR = Color(10, 10, 10)
MARGIN_ZONE = 180
NODE_LABEL_MARGINE = 8
DRONE_SPEED = 200
ARRIVAL_THRESHOLD = 5
DEPARTURE_INTERVAL = 1.0

class ZoneReservationTable:
    """Table de réservation atomique espace-temps pour zones et connexions."""

    def __init__(self):
        self._counts: dict[tuple[str, int], int] = {}

    def occupancy(self, zone: str, t: int) -> int:
        return self._counts.get((zone, t), 0)

    def try_acquire(self, zone: str, t: int, capacity: int) -> bool:
        current = self._counts.get((zone, t), 0)
        if current >= capacity:
            return False
        self._counts[(zone, t)] = current + 1
        return True


class DroneManager:
    """Gère l'état des drones, la planification sans blocage et l'animation."""

    def __init__(self, network: Network, paths: list[list[str]]):
        self.network = network

        valid_paths = []
        if paths:
            raw_paths = [paths] if isinstance(paths[0], str) else paths
            for p in raw_paths:
                if len(p) > 1 and p[0] == self.network.start and p[-1] == self.network.end:
                    if len(p) == len(set(p)):
                        valid_paths.append(p)

        self.paths: list[list[str]] = valid_paths
        self.drones: list[Drone] = network.get_drones()
        self.connections: list[Connection] = network.connections
        self._connection_lookup = self._build_connection_lookup()

        self._zone_positions: dict[str, Vector2] = {
            name: Vector2(z.x * MARGIN_ZONE, z.y * MARGIN_ZONE)
            for name, z in self.network.zones.items()
        }

        self.drone_positions: dict[str, Vector2] = {}
        self.schedule: list[list[tuple[str, str, str]]] = []
        self.current_round: int = 0
        self.round_progress: float = 0.0
        self.round_duration: float = MARGIN_ZONE / DRONE_SPEED

        self.start_simulation()

    def _build_connection_lookup(self) -> dict[tuple[str, str], Connection]:
        lookup: dict[tuple[str, str], Connection] = {}
        for conn in self.connections:
            lookup[(conn.zone_a, conn.zone_b)] = conn
            lookup[(conn.zone_b, conn.zone_a)] = conn
        return lookup

    def _zone_type(self, zone_name: str) -> str:
        zone = self.network.get_zone(zone_name)
        for attr in ("zone_type", "type", "zone"):
            val = getattr(zone, attr, None)
            if val:
                return str(val)
        return "normal"

    def _is_blocked(self, zone_name: str) -> bool:
        return self._zone_type(zone_name) == "blocked"

    def _zone_cost(self, zone_name: str) -> int:
        return 2 if self._zone_type(zone_name) == "restricted" else 1

    def _zone_capacity(self, zone_name: str) -> int:
        if zone_name in (self.network.start, self.network.end):
            return 999999
        zone = self.network.get_zone(zone_name)

        cap = getattr(zone, "max_drones", getattr(zone, "max_drone", getattr(zone, "capacity", None)))
        if cap is None and hasattr(zone, "attributes") and isinstance(zone.attributes, dict):
            cap = zone.attributes.get("max_drones", zone.attributes.get("max_drone"))
        if cap is None and hasattr(zone, "params") and isinstance(zone.params, dict):
            cap = zone.params.get("max_drones", zone.params.get("max_drone"))

        if cap is not None:
            try:
                return int(cap)
            except (ValueError, TypeError):
                pass
        return 1

    def _edge_capacity(self, zone_a: str, zone_b: str) -> int:
        conn = self._connection_lookup.get((zone_a, zone_b))
        if not conn:
            return 1
        cap = getattr(conn, "max_link_capacity", getattr(conn, "max_capacity", getattr(conn, "capacity", None)))
        if cap is None and hasattr(conn, "attributes") and isinstance(conn.attributes, dict):
            cap = conn.attributes.get("max_link_capacity", conn.attributes.get("max_capacity"))
        if cap is not None:
            try:
                return int(cap)
            except (ValueError, TypeError):
                pass
        return 999999

    def start_simulation(self) -> None:
        start_pos = self._zone_positions[self.network.start]
        for drone in self.drones:
            self.drone_positions[drone.id_drone] = Vector2(start_pos)

        self.schedule = self.compute_schedule()
        self.current_round = 0
        self.round_progress = 0.0

    def print_schedule(self) -> None:
        for i, round_moves in enumerate(self.schedule, 1):
            line = " ".join(f"{id_drone}-{zone_b}" for id_drone, _, zone_b in round_moves)
            print(f"Turn {i}   -- {line}")

    def is_finished(self) -> bool:
        return self.current_round >= len(self.schedule)

    def update_drones(self, dt: float) -> None:
        if self.is_finished() or not self.schedule:
            return

        self.round_progress += dt / self.round_duration
        t = min(self.round_progress, 1.0)

        for id_drone, zone_from, zone_to in self.schedule[self.current_round]:
            start_pos = self._zone_positions[zone_from]
            end_pos = self._zone_positions[zone_to]

            # Calcul de la progression globale pour les mouvements multi-tours
            first_round = self.current_round
            while first_round > 0 and (id_drone, zone_from, zone_to) in self.schedule[first_round - 1]:
                first_round -= 1

            last_round = self.current_round
            while last_round < len(self.schedule) - 1 and (id_drone, zone_from, zone_to) in self.schedule[last_round + 1]:
                last_round += 1

            total_turns = (last_round - first_round) + 1
            current_turn_offset = self.current_round - first_round

            global_t = (current_turn_offset + t) / total_turns
            self.drone_positions[id_drone] = start_pos.lerp(end_pos, global_t)

        if self.round_progress >= 1.0:
            for id_drone, _, zone_to in self.schedule[self.current_round]:
                self.drone_positions[id_drone] = Vector2(self._zone_positions[zone_to])
            self.current_round += 1
            self.round_progress = 0.0

    def compute_schedule(self) -> list[list[tuple[str, str, str]]]:
        adj: dict[str, list[str]] = {name: [] for name in self.network.zones}
        for conn in self.connections:
            if not self._is_blocked(conn.zone_b):
                adj[conn.zone_a].append(conn.zone_b)
            if not self._is_blocked(conn.zone_a):
                adj[conn.zone_b].append(conn.zone_a)

        end_pos = self._zone_positions[self.network.end]

        def neighbor_sort_key(nxt: str) -> tuple:
            is_priority = self._zone_type(nxt) == "priority"
            return (0 if is_priority else 1, self._zone_positions[nxt].distance_to(end_pos))

        for u in adj:
            adj[u].sort(key=neighbor_sort_key)

        node_table = ZoneReservationTable()
        edge_table = ZoneReservationTable()

        def edge_key(u: str, v: str) -> str:
            return "|".join(sorted([u, v]))

        def is_node_free(zone: str, t: int) -> bool:
            if zone in (self.network.start, self.network.end):
                return True
            return node_table.occupancy(zone, t) < self._zone_capacity(zone)

        drone_paths: dict[str, list[tuple[int, str, str, int]]] = {}
        max_t = 0
        drone_queue = deque(self.drones)
        skipped: list[Drone] = []

        while drone_queue:
            drone = drone_queue.popleft()
            d_id = drone.id_drone

            queue = deque([(0, self.network.start, {self.network.start}, [])])
            visited_time_space = {(self.network.start, 0)}
            found = None

            while queue:
                t, curr, spatial_visited, path = queue.popleft()
                if curr == self.network.end:
                    found = path
                    break
                if t > 3000:
                    break

                # 1. Traitement des déplacements vers une zone voisine
                for nxt in adj.get(curr, []):
                    if nxt in spatial_visited:
                        continue

                    cost = self._zone_cost(nxt)
                    arrival_t = t + cost
                    e_cap = self._edge_capacity(curr, nxt)
                    ekey = edge_key(curr, nxt)

                    edge_free = all(edge_table.occupancy(ekey, t + k) < e_cap for k in range(cost))
                    nxt_free = is_node_free(nxt, arrival_t)

                    if edge_free and nxt_free:
                        if (nxt, arrival_t) not in visited_time_space:
                            visited_time_space.add((nxt, arrival_t))
                            queue.append(
                                (arrival_t, nxt, spatial_visited | {nxt},
                                 path + [(t, curr, nxt, cost)])
                            )

                # 2. Attente sur la zone courante (1 tour)
                if is_node_free(curr, t + 1):
                    if (curr, t + 1) not in visited_time_space:
                        visited_time_space.add((curr, t + 1))
                        queue.append((t + 1, curr, spatial_visited, path + [(t, curr, curr, 1)]))

            if not found:
                skipped.append(drone)
                continue

            drone_paths[d_id] = found

            # Réservation définitive des créneaux validés
            for step_t, u, v, cost in found:
                if u != v:
                    ekey = edge_key(u, v)
                    e_cap = self._edge_capacity(u, v)

                    for k in range(cost):
                        edge_table.try_acquire(ekey, step_t + k, e_cap)

                    end_t = step_t + cost
                    if v not in (self.network.start, self.network.end):
                        node_table.try_acquire(v, end_t, self._zone_capacity(v))
                else:
                    end_t = step_t + 1
                    if u not in (self.network.start, self.network.end):
                        node_table.try_acquire(u, end_t, self._zone_capacity(u))

                if end_t > max_t:
                    max_t = end_t

        if skipped:
            names = ", ".join(d.id_drone for d in skipped)
            print(f"[AVERTISSEMENT] Drones sans chemin trouvé (capacité saturée) : {names}")

        schedule: list[list[tuple[str, str, str]]] = [[] for _ in range(max_t)]
        for d_id, moves in drone_paths.items():
            for step_t, u, v, cost in moves:
                if u != v:
                    for k in range(cost):
                        schedule[step_t + k].append((d_id, u, v))

        while schedule and not schedule[-1]:
            schedule.pop()

        return schedule


class Renderer:
    """Responsable du rendu graphique du réseau et des drones."""

    def __init__(self, screen: Surface, camera: Camera, network: Network, drone_manager: DroneManager, font: pygame.font.Font):
        self.screen = screen
        self.camera = camera
        self.network = network
        self.drone_manager = drone_manager
        self.zones: list[Zone] = list(network.zones.values())
        self.font = font

        self.start_img = pygame.transform.scale(pygame.image.load("image/start.png").convert_alpha(), (64, 64))
        self.end_img = pygame.transform.scale(pygame.image.load("image/end.png").convert_alpha(), (64, 64))
        self.drone_img = pygame.transform.scale(pygame.image.load("image/drone.png"), (32, 32))
        self.hub_img = pygame.transform.scale(pygame.image.load("image/hub.png").convert_alpha(), (64, 64))

    def draw_drone(self):
        for drone in self.drone_manager.drones:
            world_pos = self.drone_manager.drone_positions[drone.id_drone]
            screen_pos = self.camera.apply(world_pos)
            rect_img = self.drone_img.get_rect(center=screen_pos)
            self.screen.blit(self.drone_img, rect_img)

    def draw_connection(self):
        for conn in self.network.connections:
            zone_a = self.network.get_zone(conn.zone_a)
            zone_b = self.network.get_zone(conn.zone_b)
            pos_a = self.camera.apply(Vector2(zone_a.x * MARGIN_ZONE, zone_a.y * MARGIN_ZONE))
            pos_b = self.camera.apply(Vector2(zone_b.x * MARGIN_ZONE, zone_b.y * MARGIN_ZONE))
            pygame.draw.line(self.screen, Color(0, 200, 210), pos_a, pos_b, 2)

    def draw_nodes(self):
        for zone in self.zones:
            if zone.name == self.network.start:
                image = self.start_img
            elif zone.name == self.network.end:
                image = self.end_img
            else:
                image = self.hub_img

            try:
                tint_color = Color(zone.color)
            except ValueError:
                tint_color = Color("White")

            tint = image.copy()
            tint.fill(tint_color, special_flags=pygame.BLEND_RGBA_MULT)

            pos = Vector2(zone.x * MARGIN_ZONE, zone.y * MARGIN_ZONE)
            screen_pos = self.camera.apply(pos)

            img_rect = tint.get_rect(center=screen_pos)
            self.screen.blit(tint, img_rect)

            label_name = self.font.render(zone.name, True, Color("yellow"))
            bg_rect = label_name.get_rect(center=(screen_pos.x, img_rect.top - NODE_LABEL_MARGINE))

            padding_rect = bg_rect.inflate(6, 4)
            pygame.draw.rect(self.screen, Color(10, 10, 15, 220), padding_rect, border_radius=3)
            self.screen.blit(label_name, bg_rect)

    def draw_turn_info(self):
        total_turns = len(self.drone_manager.schedule)
        current_turn = min(self.drone_manager.current_round + 1, total_turns) if total_turns > 0 else 0
    
        # Texte du tour actuel / total
        turn_text = f"Tour : {current_turn} / {total_turns}"
        label = self.font.render(turn_text, True, Color("cyan"))
    
        # Arrière-plan pour la lisibilité
        rect = label.get_rect(topleft=(20, 20))
        bg_rect = rect.inflate(12, 8)
        pygame.draw.rect(self.screen, Color(10, 10, 15, 220), bg_rect, border_radius=4)
        self.screen.blit(label, rect)
    
        # Affichage optionnel des mouvements du tour courant
        if 0 <= self.drone_manager.current_round < total_turns:
            moves = self.drone_manager.schedule[self.drone_manager.current_round]
            moves_str = " | ".join(f"{d}-{z_to}" for d, _, z_to in moves)
            moves_label = self.font.render(f"Mouvements : {moves_str}", True, Color("white"))
            
            moves_rect = moves_label.get_rect(topleft=(20, 55))
            moves_bg = moves_rect.inflate(12, 8)
            pygame.draw.rect(self.screen, Color(10, 10, 15, 220), moves_bg, border_radius=4)
            self.screen.blit(moves_label, moves_rect)

class InputHandler:
    """Gère les entrées clavier pour la caméra."""

    def __init__(self, camera: Camera):
        self.camera = camera

    def get_direction(self) -> Vector2:
        keys = pygame.key.get_pressed()
        direction = Vector2(0, 0)

        if keys[pygame.K_UP]:
            direction.y -= 1
        if keys[pygame.K_DOWN]:
            direction.y += 1
        if keys[pygame.K_LEFT]:
            direction.x -= 1
        if keys[pygame.K_RIGHT]:
            direction.x += 1
        return direction

    def handle_input(self) -> None:
        keys = pygame.key.get_pressed()
        max_zoom = 1.0
        min_zoom = 0.25
        step = 0.05

        if keys[pygame.K_w]:
            new_zoom = min(max_zoom, self.camera.get_zoom() + step)
            self.camera.set_zoom(new_zoom)
        elif keys[pygame.K_s]:
            new_zoom = max(min_zoom, self.camera.get_zoom() - step)
            self.camera.set_zoom(new_zoom)


class Interface:
    """Orchestre l'initialisation et la boucle principale Pygame."""

    def __init__(self, w: int = 1200, h: int = 800, network: Network | None = None,
                 drone_manager: DroneManager | None = None):
        pygame.init()
        pygame.font.init()

        self.font = pygame.font.Font(None, 24)
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Fly-in")
        self.fps = 60
        self.network = network
        self.camera: Camera = Camera((0, 0), 500, 0.5)

        self.drone_manager = drone_manager if drone_manager else DroneManager(
            network, find_all_paths(network)
        )
        self.renderer = Renderer(self.screen, self.camera, self.network, self.drone_manager, self.font)
        self.input_handler = InputHandler(self.camera)
        self.clock = pygame.time.Clock()

        # Variable d'état pour gérer la pause
        self.is_paused: bool = False

    def running(self):
        run = True
        while run:
            dt = self.clock.tick(self.fps) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        run = False
                    # Basculer l'état de pause avec la touche ESPACE ou P
                    elif event.key in (pygame.K_SPACE, pygame.K_p):
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_r:
                        self.drone_manager.start_simulation()
                        self.is_paused = False

            # Dans Interface.running()
            self.screen.fill(BG_COLOR)

            self.renderer.draw_connection()
            self.renderer.draw_nodes()
            
            if not self.is_paused:
                self.drone_manager.update_drones(dt)
                dir_cam = self.input_handler.get_direction()
                self.camera.update(self.screen, dir_cam, dt)
            
            self.renderer.draw_drone()
            
            # --- AJOUTER CETTE LIGNE ---
            self.renderer.draw_turn_info()
            
            if self.is_paused:
                pause_label = self.font.render("PAUSE (Appuyez sur ESPACE pour reprendre)", True, Color("orange"))
                self.screen.blit(pause_label, (20, 90))  # Décalé pour ne pas superposer les informations
            
            self.input_handler.handle_input()
            pygame.display.update()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Fly-in : simulation de drones")
    parser.add_argument("map_file", help="Fichier de carte .gph")
    parser.add_argument("--visu", action="store_true",
                         help="Ouvre l'affichage visuel pygame (sans sortie texte)")
    args = parser.parse_args()

    net = NetworkParser(args.map_file).parse()
    paths = find_all_paths(net)

    drone_manager = DroneManager(net, paths)

    if args.visu:
        interface = Interface(network=net, drone_manager=drone_manager)
        interface.running()
    else:
        drone_manager.print_schedule()


if __name__ == "__main__":
    main()