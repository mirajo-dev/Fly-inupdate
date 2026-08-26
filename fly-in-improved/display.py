from __future__ import annotations

from typing import Final

import pygame
from pygame.math import Vector2

from algo_A_star import RoutePlan
from parsing.network import Network
from simulation import Simulation


class SimulationApp:
    """Interactive pygame visualization of the discrete drone simulation."""

    WIDTH: Final[int] = 1200
    HEIGHT: Final[int] = 780
    FPS: Final[int] = 60

    def __init__(self, network: Network, plan: RoutePlan) -> None:
        pygame.init()
        pygame.font.init()
        self.network = network
        self.plan = plan
        self.simulation = Simulation(network, plan)

        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Fly-in Drones — Routing Simulation")

        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.ui_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 13)
        self.label_font = pygame.font.SysFont("Arial", 14, bold=True)

        self.background = (17, 21, 29)
        self.panel = (25, 31, 42)
        self.grid = (38, 47, 61)
        self.text = (235, 240, 247)
        self.muted = (155, 167, 184)
        self.cyan = (52, 211, 235)
        self.green = (68, 220, 145)
        self.orange = (247, 177, 77)
        self.red = (235, 91, 91)
        self.purple = (174, 126, 255)

        self.map_rect = pygame.Rect(24, 94, 840, 650)
        self.side_rect = pygame.Rect(884, 94, 292, 650)

        self.positions = self._calculate_positions()
        self.images = self._load_images()
        self.running = True
        self.paused = False
        self.auto_step = True
        self.animation = 0.0
        self.turn_duration = 0.65
        self.last_turn_number = 0

    def _load_images(self) -> dict[str, pygame.Surface]:
        """Load optional project icons, falling back to drawn shapes."""
        result: dict[str, pygame.Surface] = {}
        for key, filename in (
            ("start", "image/start.png"),
            ("end", "image/end.png"),
            ("hub", "image/hub.png"),
            ("drone", "image/drone.png"),
        ):
            try:
                image = pygame.image.load(filename).convert_alpha()
                result[key] = image
            except (pygame.error, FileNotFoundError):
                pass
        return result

    def _calculate_positions(self) -> dict[str, tuple[int, int]]:
        """Scale map coordinates into the visualization area."""
        zones = list(self.network.zones.values())
        if not zones:
            return {}

        min_x = min(zone.x for zone in zones)
        max_x = max(zone.x for zone in zones)
        min_y = min(zone.y for zone in zones)
        max_y = max(zone.y for zone in zones)

        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
        margin = 80
        usable_w = self.map_rect.width - 2 * margin
        usable_h = self.map_rect.height - 2 * margin

        return {
            name: (
                self.map_rect.left + margin
                + int((zone.x - min_x) / width * usable_w),
                self.map_rect.top + margin
                + int((zone.y - min_y) / height * usable_h),
            )
            for name, zone in self.network.zones.items()
        }

    def _zone_color(self, zone_type: str) -> tuple[int, int, int]:
        """Return a stable UI color for a zone type."""
        return {
            "normal": (83, 99, 121),
            "priority": self.green,
            "restricted": self.orange,
            "blocked": self.red,
        }.get(zone_type, (83, 99, 121))

    def _draw_background(self) -> None:
        """Draw the application panels and a subtle grid."""
        self.screen.fill(self.background)
        for x in range(self.map_rect.left, self.map_rect.right, 40):
            pygame.draw.line(
                self.screen, self.grid,
                (x, self.map_rect.top), (x, self.map_rect.bottom), 1,
            )
        for y in range(self.map_rect.top, self.map_rect.bottom, 40):
            pygame.draw.line(
                self.screen, self.grid,
                (self.map_rect.left, y), (self.map_rect.right, y), 1,
            )
        pygame.draw.rect(self.screen, self.panel, self.side_rect, border_radius=12)
        pygame.draw.rect(self.screen, self.panel, (24, 18, 1152, 58), border_radius=12)

    def _draw_connections(self) -> None:
        """Draw all links, emphasizing the routes actually assigned."""
        assigned_edges: set[frozenset[str]] = set()
        for route in self.plan.routes:
            assigned_edges.update(
                frozenset((route[index], route[index + 1]))
                for index in range(len(route) - 1)
            )

        for connection in self.network.connections:
            a = self.positions[connection.zone_a]
            b = self.positions[connection.zone_b]
            key = frozenset((connection.zone_a, connection.zone_b))
            color = self.cyan if key in assigned_edges else self.grid
            width = 4 if key in assigned_edges else 2
            pygame.draw.line(self.screen, color, a, b, width)

            mid = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
            capacity = self.small_font.render(
                f"x{connection.max_link_capacity}", True, self.muted
            )
            self.screen.blit(capacity, (mid[0] + 5, mid[1] + 5))

    def _draw_nodes(self) -> None:
        """Draw hubs with colors and capacity labels."""
        for name, zone in self.network.zones.items():
            pos = self.positions[name]
            radius = 24 if name in (self.network.start, self.network.end) else 20
            color = self.green if name == self.network.start else (
                self.purple if name == self.network.end else self._zone_color(zone.zone_type)
            )
            pygame.draw.circle(self.screen, (10, 13, 18), pos, radius + 4)
            pygame.draw.circle(self.screen, color, pos, radius)
            pygame.draw.circle(self.screen, (230, 235, 242), pos, radius, 2)

            label = self.label_font.render(name, True, self.text)
            self.screen.blit(label, (pos[0] - label.get_width() // 2, pos[1] + 29))

            if zone.zone_type != "normal" or zone.max_drones != 1:
                info = self.small_font.render(
                    f"{zone.zone_type} · cap {zone.max_drones}",
                    True,
                    self.muted,
                )
                self.screen.blit(
                    info,
                    (pos[0] - info.get_width() // 2, pos[1] + 46),
                )

    def _drone_position(self, drone_id: int) -> tuple[int, int]:
        """Return an interpolated position for a moving drone."""
        drone = self.simulation.drones[drone_id - 1]
        if drone.transit_connection is not None:
            source, destination = drone.transit_connection
            start = Vector2(self.positions[source])
            end = Vector2(self.positions[destination])
            progress = 1.0 - drone.transit_remaining / 2.0
            position = start.lerp(end, max(0.0, min(1.0, progress)))
            return int(position.x), int(position.y)

        current = drone.current_zone
        if drone.last_move and self.animation < 1.0:
            source, destination = drone.last_move
            start = Vector2(self.positions[source])
            end = Vector2(self.positions[destination])
            position = start.lerp(end, self.animation)
            return int(position.x), int(position.y)

        return self.positions[current]

    def _draw_drones(self) -> None:
        """Draw all non-delivered drones."""
        for drone in self.simulation.drones:
            if drone.delivered:
                continue
            x, y = self._drone_position(drone.drone_id)
            if "drone" in self.images:
                image = pygame.transform.smoothscale(self.images["drone"], (34, 34))
                rect = image.get_rect(center=(x, y))
                self.screen.blit(image, rect)
            else:
                pygame.draw.circle(self.screen, self.cyan, (x, y), 12)
                pygame.draw.circle(self.screen, self.text, (x, y), 12, 2)

            label = self.small_font.render(
                f"D{drone.drone_id}", True, self.text
            )
            self.screen.blit(label, (x - label.get_width() // 2, y - 29))

    def _draw_header(self) -> None:
        """Draw title and global turn counters."""
        title = self.title_font.render("FLY-IN DRONES", True, self.text)
        self.screen.blit(title, (42, 31))

        delivered = sum(drone.delivered for drone in self.simulation.drones)
        stats = (
            f"Turn {self.simulation.turn}   •   "
            f"Delivered {delivered}/{self.network.nb_drones}   •   "
            f"{'PAUSED' if self.paused else 'RUNNING'}"
        )
        surface = self.ui_font.render(stats, True, self.cyan)
        self.screen.blit(surface, (330, 34))

    def _draw_side_panel(self) -> None:
        """Draw controls, route summary, and legend."""
        x = self.side_rect.left + 20
        y = self.side_rect.top + 20

        heading = self.ui_font.render("Simulation", True, self.text)
        self.screen.blit(heading, (x, y))
        y += 34

        lines = [
            "SPACE  pause / resume",
            "N      next turn",
            "R      reset",
            "UP     faster",
            "DOWN   slower",
            "",
            f"Turn duration: {self.turn_duration:.2f}s",
            f"Routes: {len(set(self.plan.routes))}",
        ]
        for line in lines:
            surface = self.small_font.render(line, True, self.muted)
            self.screen.blit(surface, (x, y))
            y += 22

        y += 12
        legend = self.ui_font.render("Zone types", True, self.text)
        self.screen.blit(legend, (x, y))
        y += 30

        for zone_type in ("normal", "priority", "restricted", "blocked"):
            pygame.draw.circle(
                self.screen, self._zone_color(zone_type), (x + 8, y + 7), 7
            )
            label = self.small_font.render(zone_type, True, self.text)
            self.screen.blit(label, (x + 24, y))
            y += 24

        y += 12
        recent = self.ui_font.render("Latest turn", True, self.text)
        self.screen.blit(recent, (x, y))
        y += 30

        if not self.simulation.history:
            text = "No movement yet."
            self.screen.blit(self.small_font.render(text, True, self.muted), (x, y))
        else:
            movements = self.simulation.history[-1].movements
            if not movements:
                text = "Waiting — capacities are full."
                self.screen.blit(self.small_font.render(text, True, self.orange), (x, y))
            else:
                for movement in movements[:8]:
                    text = f"D{movement.drone_id}: {movement.source} → {movement.destination}"
                    self.screen.blit(self.small_font.render(text, True, self.text), (x, y))
                    y += 20

    def _advance_turn(self) -> None:
        """Advance one discrete simulation turn."""
        if self.simulation.finished:
            return
        self.simulation.step_once()
        self.animation = 0.0
        self.last_turn_number = self.simulation.turn

    def reset(self) -> None:
        """Reset the simulation to turn zero."""
        self.simulation = Simulation(self.network, self.plan)
        self.animation = 0.0

    def run(self) -> None:
        """Run the pygame event loop."""
        clock = pygame.time.Clock()

        while self.running:
            dt = clock.tick(self.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_n:
                        self._advance_turn()
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_UP:
                        self.turn_duration = max(0.15, self.turn_duration - 0.05)
                    elif event.key == pygame.K_DOWN:
                        self.turn_duration = min(2.0, self.turn_duration + 0.05)

            if not self.paused and self.auto_step:
                self.animation += dt / self.turn_duration
                if self.animation >= 1.0:
                    self._advance_turn()

            self._draw_background()
            self._draw_header()
            self._draw_connections()
            self._draw_nodes()
            self._draw_drones()
            self._draw_side_panel()
            pygame.display.flip()

        pygame.quit()
