import pygame
from pygame.math import Vector2
from parsing.network import Network
from algo_A_star import *


class Drone:

    def __init__(
        self,
        drone_id: int,
        path: list[str],
        positions: dict[str, tuple[int, int]],
    ):
        self.drone_id = drone_id
        self.path = path
        self.current_step = 0

        start_zone = self.path[0] if self.path else ""
        initial_coords = positions.get(start_zone, (0, 0))
        self.pos = Vector2(initial_coords)

        self.speed = 3.0
        self.delay = drone_id * 40
        self.has_started = False
        self.has_finished = False
        self.is_moving = False
        self.angle = 0.0

    def update(
        self,
        positions: dict[str, tuple[int, int]],
        occupied_hubs: set[str],
        start_zone: str,
        end_zone: str,
    ) -> bool:
        """Déplace le drone et retourne True lorsqu'une étape (hub à hub) est complétée."""
        if self.has_finished:
            return False

        if self.delay > 0:
            self.delay -= 1
            return False

        self.has_started = True

        if self.current_step < len(self.path) - 1:
            current_hub = self.path[self.current_step]
            next_hub = self.path[self.current_step + 1]

            if not self.is_moving:
                if next_hub in occupied_hubs and next_hub != end_zone:
                    return False

                if next_hub != end_zone:
                    occupied_hubs.add(next_hub)
                if current_hub in occupied_hubs and current_hub != start_zone:
                    occupied_hubs.remove(current_hub)

                self.is_moving = True

            target_pos = Vector2(positions[next_hub])
            direction = target_pos - self.pos
            distance = direction.length()

            if distance > 0:
                self.angle = Vector2(0, -1).angle_to(direction)

            if distance <= self.speed:
                self.pos = target_pos
                self.current_step += 1
                self.is_moving = False
                return True  # Un déplacement de tour a été effectué !
            else:
                direction.normalize_ip()
                self.pos += direction * self.speed
                return False
        else:
            final_hub = self.path[-1]
            if final_hub in occupied_hubs and final_hub != end_zone:
                occupied_hubs.remove(final_hub)
            self.has_finished = True
            return False


class Graphe:

    def __init__(self, network: Network):
        pygame.init()
        pygame.font.init()

        self.width = 900
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-in - Simulation drones")

        self.network = network

        self.font = pygame.font.SysFont("Arial", 14, bold=True)
        self.drone_font = pygame.font.SysFont("Arial", 11, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.title_font = pygame.font.SysFont("Arial", 17, bold=True)

        self.start_img = pygame.image.load("image/start.png")
        self.start_img = pygame.transform.scale(self.start_img, (72, 72))

        self.goal_img = pygame.image.load("image/end.png")
        self.goal_img = pygame.transform.scale(self.goal_img, (72, 72))

        self.hub_img = pygame.image.load("image/hub.png").convert_alpha()
        self.hub_img = pygame.transform.scale(self.hub_img, (64, 64))

        self.drone_img = pygame.image.load("image/drone.png")
        self.drone_img = pygame.transform.scale(self.drone_img, (32, 32))

        self.positions = self.calculate_positions()

        self.path = a_star(self.network)
        print(f"Chemin pour les drones : {self.path}")

        self.drones = [
            Drone(i, self.path, self.positions)
            for i in range(self.network.nb_drones)
        ]

        self.occupied_hubs = set()
        self.is_paused = False
        self.speed_factor = 1.0

        # Compteur total des tours effectués par l'ensemble des drones
        self.total_tours = 0

    def calculate_positions(self) -> dict[str, tuple[int, int]]:
        margin = 80
        zones = list(self.network.zones.values())

        if not zones:
            return {}

        x_vals = [z.x for z in zones]
        y_vals = [z.y for z in zones]

        min_x, max_x = min(x_vals), max(x_vals)
        min_y, max_y = min(y_vals), max(y_vals)

        range_x = (max_x - min_x) if max_x != min_x else 1
        range_y = (max_y - min_y) if max_y != min_y else 1

        usable_w = self.width - (2 * margin)
        usable_h = self.height - (2 * margin)

        scaled_pos = {}
        for name, zone in self.network.zones.items():
            screen_x = margin + int((zone.x - min_x) / range_x * usable_w)
            screen_y = margin + int((zone.y - min_y) / range_y * usable_h)
            scaled_pos[name] = (screen_x, screen_y)

        return scaled_pos

    def reset(self):
        """Réinitialise les drones, le compteur et les réservations."""
        self.drones = [
            Drone(i, self.path, self.positions)
            for i in range(self.network.nb_drones)
        ]
        self.occupied_hubs.clear()
        self.is_paused = False
        self.total_tours = 0

    def draw_drones(self):
        """Dessine chaque drone actif orienté selon sa direction."""
        for drone in self.drones:
            if drone.has_started:
                px, py = int(drone.pos.x), int(drone.pos.y)

                rotated_img = pygame.transform.rotate(
                    self.drone_img, -drone.angle
                )
                rect = rotated_img.get_rect(center=(px, py))
                self.screen.blit(rotated_img, rect)

                id_text = self.drone_font.render(
                    f"D{drone.drone_id}", True, (255, 255, 255)
                )
                bg_rect = pygame.Rect(px - 10, py - 24, 20, 14)
                pygame.draw.rect(
                    self.screen, (20, 20, 30), bg_rect, border_radius=3
                )
                self.screen.blit(id_text, (px - 7, py - 24))

    def draw_ui(self):
        """Affiche le bandeau supérieur avec le NOMBRE TOTAL DE TOURS bien en évidence."""
        arrived_count = sum(1 for d in self.drones if d.has_finished)
        active_count = sum(
            1 for d in self.drones if d.has_started and not d.has_finished
        )

        # 1. Barre d'informations générales (gauche)
        info_text = f"Drones: {len(self.drones)} | En vol: {active_count} | Arrivés: {arrived_count} | Vitesse: x{self.speed_factor:.2f}"
        info_surf = self.ui_font.render(info_text, True, (210, 220, 235))

        pygame.draw.rect(
            self.screen, (15, 20, 28), (10, 10, 520, 36), border_radius=6
        )
        self.screen.blit(info_surf, (20, 18))

        # 2. Encadré vert fluo pour le NOMBRE TOTAL DE TOURS (droite)
        tour_text = f"TOURS TOTAUX : {self.total_tours}"
        tour_surf = self.title_font.render(tour_text, True, (0, 255, 200))

        box_width = tour_surf.get_width() + 30
        box_rect = pygame.Rect(self.width - box_width - 15, 10, box_width, 36)

        pygame.draw.rect(self.screen, (15, 30, 40), box_rect, border_radius=6)
        pygame.draw.rect(
            self.screen, (0, 255, 200), box_rect, width=2, border_radius=6
        )
        self.screen.blit(tour_surf, (self.width - box_width, 17))

        if self.is_paused:
            pause_surf = self.ui_font.render(
                "PAUSE - Appuyez sur ESPACE pour reprendre", True, (255, 200, 0)
            )
            px = self.width // 2 - pause_surf.get_width() // 2
            pygame.draw.rect(
                self.screen,
                (40, 30, 0),
                (px - 10, 52, pause_surf.get_width() + 20, 28),
                border_radius=5,
            )
            self.screen.blit(pause_surf, (px, 56))

    def draw_connections(self):
        """Dessine les liaisons entre les zones."""
        for conn in self.network.connections:
            hub_a, hub_b = conn.zone_a, conn.zone_b
            if hub_a in self.positions and hub_b in self.positions:
                pos_a = self.positions[hub_a]
                pos_b = self.positions[hub_b]

                is_main_path = any(
                    (self.path[i] == hub_a and self.path[i + 1] == hub_b)
                    or (self.path[i] == hub_b and self.path[i + 1] == hub_a)
                    for i in range(len(self.path) - 1)
                )
                color = (0, 220, 255) if is_main_path else (40, 60, 80)
                width = 4 if is_main_path else 2

                pygame.draw.line(self.screen, color, pos_a, pos_b, width)

    def draw_nodes(self):
        """Dessine les zones et leurs noms."""
        for name, pos in self.positions.items():
            if name == self.network.start:
                selected_img = self.start_img
            elif name == self.network.end:
                selected_img = self.goal_img
            else:
                selected_img = self.hub_img

            image_rect = selected_img.get_rect(center=pos)
            self.screen.blit(selected_img, image_rect)

            label = self.font.render(name, True, (240, 240, 240))
            self.screen.blit(label, (pos[0] - 20, pos[1] - 50))

    def running(self):
        running = True
        clock = pygame.time.Clock()

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_UP:
                        self.speed_factor = min(self.speed_factor + 0.5, 4.0)
                    elif event.key == pygame.K_DOWN:
                        self.speed_factor = max(self.speed_factor - 0.5, 0.25)

            if not self.is_paused:
                for drone in self.drones:
                    # Incrémente la somme globale dès qu'un drone valide une étape
                    if drone.update(
                        self.positions,
                        self.occupied_hubs,
                        self.network.start,
                        self.network.end,
                    ):
                        self.total_tours += 1

            self.screen.fill((24, 28, 36))
            self.draw_connections()
            self.draw_nodes()
            self.draw_drones()
            self.draw_ui()

            pygame.display.update()
            clock.tick(int(60 * self.speed_factor))

        pygame.quit()