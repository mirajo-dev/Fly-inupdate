import sys
import pygame
from pygame import Color, Surface, Vector2
from parsing.network import Network, NetworkParser
from parsing.parse_hub_config import Zone
from parsing.parse_nb_drone import Drone
from parsing.parse_connexion import Connection
from camera import Camera
from algo_A_star import a_star


pygame.font.init()
BG_COLOR = Color(10, 10, 10)
MARGIN_ZONE = 180
NODE_LABEL_MARGINE = 8
DRONE_SPEED = 200
ARRIVAL_THRESHOLD = 5
DEPARTURE_INTERVAL = 1.0
FONT = pygame.font.Font(None, 32)


class Interface:
    def __init__(self, w: int = 1200, h: int = 800, network: Network | None = None):
        self.screen = pygame.display.set_mode((999, 666))
        pygame.display.set_caption("Fly-in")
        self.fps = 60
        self.network = network
        self.zones: list[Zone] = self._init_zones()
        self.drones: list[Drone] = self._init_drones()
        self.connections: list[Connection] = self._init_connections()
        self.path: list[str] = a_star(self.network)
        
        self.drone_positions: dict[str, Vector2] = {}
        self.drone_path_index: dict[str, int] = {}
        self.drone_delay: dict[str, float] = {}

        for i, drone in enumerate(self.drones):
            start_zone = self.network.get_zone(self.path[0])
            start_pos = Vector2(start_zone.x * MARGIN_ZONE, start_zone.y * MARGIN_ZONE)
            self.drone_positions[drone.id_drone] = start_pos
            self.drone_path_index[drone.id_drone] = 0
            self.drone_delay[drone.id_drone] = i * DEPARTURE_INTERVAL
        self.camera: Camera = Camera((0,0), 500, 0.5)
        
        """Image pour le zone start"""
        self.start_img = pygame.image.load("image/start.png").convert_alpha()
        self.start_img = pygame.transform.scale(self.start_img, (64, 64))
        
        """Image pour le zone end"""
        self.end_img = pygame.image.load("image/end.png").convert_alpha()
        self.end_img = pygame.transform.scale(self.end_img, (64, 64))
        
        """Image pour le zone drone"""
        self.drone_img = pygame.image.load("image/drone.png")
        self.drone_img = pygame.transform.scale(self.drone_img, (32, 32))
        
        """Image pour le zone hub"""
        self.hub_img = pygame.image.load("image/hub.png").convert_alpha()
        self.hub_img = pygame.transform.scale(self.hub_img, (64, 64))
        
        
        self.clock = pygame.time.Clock()

        
    def _init_screen(self):
        pygame.init()

    def _init_zones(self):
        zones: list[Zone] = []
        for zone in self.network.zones.values():
            zones.append(zone)
        return zones

    def _init_drones(self):
        return self.network.get_drones()
    
    def _init_connections(self):
        return self.network.connections

    def draw_zone(self):
        for zone in self.zones:
            pos: Vector2 = Vector2(zone.x * MARGIN_ZONE, zone.y * MARGIN_ZONE)
            pos = self.camera.apply(pos)
            
    # def draw_drone(self):
    #     for drone in self.drones:
    #         current_zone = self.network.get_zone(drone.current_zone)
    #         pos: Vector2 = Vector2(current_zone.x * MARGIN_ZONE, current_zone.y * MARGIN_ZONE)
    #         image = self.drone_img
    #         pos = self.camera.apply(pos)
    #         rect_img = image.get_rect(center=pos)
    #         self.screen.blit(image, rect_img)
    def draw_drone(self):
        for drone in self.drones:
            world_pos = self.drone_positions[drone.id_drone]
            screen_pos = self.camera.apply(world_pos)
            image = self.drone_img
            rect_img = image.get_rect(center=screen_pos)
            self.screen.blit(image, rect_img)
            
    def draw_connection(self):
        for conn in self.connections:
            zone_a = self.network.get_zone(conn.zone_a)
            zone_b = self.network.get_zone(conn.zone_b)
            pos_a = self.camera.apply(Vector2(zone_a.x * MARGIN_ZONE, zone_a.y * MARGIN_ZONE))
            pos_b = self.camera.apply(Vector2(zone_b.x * MARGIN_ZONE, zone_b.y * MARGIN_ZONE))
            pygame.draw.line(self.screen, Color(0, 200, 210), pos_a, pos_b)

    def draw_nodes(self):
        for zone in self.zones:            
            if zone.name == self.network.start:
                image = self.start_img
            elif zone.name == self.network.end:
                image = self.end_img
            else:
                image = self.hub_img
                
            tint = image.copy()
            tint.fill(Color(zone.color), special_flags=pygame.BLEND_RGBA_MULT)
            
            pos = Vector2(zone.x * MARGIN_ZONE, zone.y * MARGIN_ZONE)
            screen_pos = self.camera.apply(pos)
            
            img_rect = tint.get_rect(center=screen_pos)
            self.screen.blit(tint, img_rect)
            
            label_name: Surface = FONT.render(zone.name, 1, Color("orange"))
            label_rect = label_name.get_rect(midbottom=(screen_pos.x, img_rect.top - NODE_LABEL_MARGINE))
            self.screen.blit(label_name, label_rect)
            
    def update_drones(self, dt: float):
        for drone in self.drones:
            if self.drone_delay[drone.id_drone] > 0:
                self.drone_delay[drone.id_drone] -= dt
                continue  # ce drone n'a pas encore décollé
            
            index = self.drone_path_index[drone.id_drone]
            if index >= len(self.path) - 1:
                continue
            
            target_zone = self.network.get_zone(self.path[index + 1])
            target_pos = Vector2(target_zone.x * MARGIN_ZONE, target_zone.y * MARGIN_ZONE)
            current_pos = self.drone_positions[drone.id_drone]
            direction = target_pos - current_pos
            distance = direction.length()
    
            if distance < ARRIVAL_THRESHOLD:
                self.drone_positions[drone.id_drone] = target_pos
                self.drone_path_index[drone.id_drone] += 1
                drone.current_zone = self.path[index + 1]
            else:
                direction = direction.normalize()
                self.drone_positions[drone.id_drone] += direction * DRONE_SPEED * dt

    @staticmethod
    def get_direction() -> Vector2:
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

    def Input(self) -> None:
        keys = pygame.key.get_pressed()
        max_zoom = 1
        min_zoom = 0.25
        step = 0.05
        if keys[pygame.K_w]:
            current_zoom = self.camera.get_zoom()
            new_zoom = current_zoom + step
            if new_zoom < min_zoom:
                new_zoom = min_zoom
            if new_zoom > max_zoom:
                new_zoom = max_zoom
            self.camera.set_zoom(new_zoom)
        elif keys[pygame.K_s]:
            current_zoom = self.camera.get_zoom()
            new_zoom = current_zoom - step
            if new_zoom < min_zoom:
                new_zoom = min_zoom
            if new_zoom > max_zoom:
                new_zoom = max_zoom
            self.camera.set_zoom(new_zoom)

    def running(self):
        self._init_screen()
        run = True

        while run:
            dt = self.clock.tick(self.fps) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        run = False

            self.screen.fill(BG_COLOR)

            self.draw_connection()
            self.draw_nodes()
            self.update_drones(dt)
            self.draw_drone()
            dir_cam = self.get_direction()
            self.camera.update(self.screen, dir_cam, dt)
            self.Input()
            pygame.display.update()            


if __name__ == "__main__":
    network = NetworkParser(sys.argv[1]).parse()
    interface = Interface(network=network)
    interface.running()
