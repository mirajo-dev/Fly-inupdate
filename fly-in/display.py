import pygame
from parsing.network import Network


class Drone:
    def __init__(self, drone_id: int, start_zone: str):
        self.drone_id = drone_id
        self.start_zone = start_zone
        
    


class Graphe:
    def __init__(self, network: Network):
        pygame.init()
        pygame.font.init()

        """ Dimensions de la fenêtre """
        self.width = 900
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Fly-in")

        self.network = network

        """ Police pour afficher les noms de zones """
        self.font = pygame.font.SysFont("Arial", 14, bold=True)
        
        """Image du start"""
        self.start_img = pygame.image.load("image/start.png")
        self.start_img = pygame.transform.scale(self.start_img, (36 + 36, 36 + 36))
        
        """Imade du goal"""
        self.goal_img = pygame.image.load("image/end.png")
        self.goal_img = pygame.transform.scale(self.goal_img, (36 + 36, 36 + 36))

        """ Image du hub """
        self.hub_img = pygame.image.load("image/hub.png").convert_alpha()
        self.hub_img = pygame.transform.scale(self.hub_img, (64, 64))
        """ Image du drone"""
        self.drone_img = pygame.image.load("image/drone.png")
        self.drone_img = pygame.transform.scale(self.drone_img, (32, 32))
        
        self.drones = [Drone(i, self.network.start) for i in range(self.network.nb_drones)]

        """ ÉTAPE 1 : Calcul des positions réajustées pour la fenêtre """
        self.positions = self.calculate_positions()

    def calculate_positions(self) -> dict[str, tuple[int, int]]:
        """Étape 1 : Adapte les coordonnées x, y du fichier à la taille de l'écran."""
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
    
    def draw_drone(self):
        for drone in self.drones:
            if drone.start_zone in self.positions:
                pos = self.positions[drone.start_zone]
                rect = self.drone_img.get_rect(center=pos)
                self.screen.blit(self.drone_img, rect)

    def draw_connections(self):
        """Étape 2 : Dessine les liaisons avec ombre portée en relief."""
        for conn in self.network.connections:
            hub_a = conn.zone_a
            hub_b = conn.zone_b
            
            pos_a = self.positions[hub_a]
            pos_b = self.positions[hub_b]
            pygame.draw.line(
                self.screen,
                (50, 150, 217),
                pos_a,
                pos_b,
                2
            )


    def draw_nodes(self):
        """Étape 3 : Dessine l'image de chaque zone et son nom par-dessus."""

        for name, pos in self.positions.items():
            """Image du hub centrée """
            if name == self.network.start:
                selected_img = self.start_img
            elif name == self.network.end:
                selected_img = self.goal_img
            else:
                selected_img = self.hub_img
                
            image_rect = selected_img.get_rect(center=pos)
            self.screen.blit(selected_img, image_rect)
            """ Nom de la zone """
            label = self.font.render(name, True, (240, 240, 240))
            self.screen.blit(label, (pos[0] - 20, pos[1] - 66))

    from pygame import Vector2

    def running(self):
        """Boucle de jeu (Game Loop)."""
        running = True
        clock = pygame.time.Clock()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Ordre de dessin des calques
            """1. Arrière-plan"""
            self.screen.fill((24, 28, 36))  
            self.draw_connections()
            self.draw_nodes()
            self.draw_drone()
            pygame.display.update()
            clock.tick(60)

        pygame.quit()