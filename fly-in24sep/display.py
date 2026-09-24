"""Scheduling, text output and pygame rendering for the Fly-in simulation.

The module computes a turn-by-turn schedule that moves every drone from
the start zone to the end zone while respecting zone and connection
capacities. The schedule is either printed in the terminal or animated
in a pygame window (``--visuel``).

Usage:
    python3 display.py <map_file> [--visuel]

The module exits with an error message if ``pygame`` is not installed.
"""

from algo_A_star import find_all_paths
import argparse
import sys

from network import Network, NetworkParser
from display_tools import DroneManager, InputHandler, Renderer
from camera import Camera
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
try:
    import pygame
    from pygame import Color, Vector2
except ImportError:
    print("[Error] Missing 'pygame' module.")
    print(" Required inst Required installation: 'pip install pygame'")
    sys.exit(1)

BG_COLOR = Color(10, 10, 10)

class Interface:
    """Orchestrates the pygame initialization and the main loop.

    Attributes:
        font: Font used for labels.
        screen: Display surface.
        fps: Target number of frames per second.
        network: Network to display.
        camera: Camera used to navigate the map.
        drone_manager: Manager of the drones and of the schedule.
        renderer: Renderer drawing the scene.
        input_handler: Handler of the camera keys.
        clock: Clock used to limit the frame rate.
        is_paused: Whether the simulation is paused.
    """

    def __init__(
            self,
            w: int = 1200,
            h: int = 800,
            network: Network | None = None,
            drone_manager: DroneManager | None = None) -> None:
        """Initializes pygame, the window and the helper objects.

        Args:
            w: Window width, in pixels.
            h: Window height, in pixels.
            network: Network to display.
            drone_manager: Existing manager to use. If ``None``, a new one
                is created from the paths of the network.

        Raises:
            ValueError: If ``network`` is ``None``.
        """
        if network is None:
            raise ValueError("Interface requires a network")

        pygame.init()
        pygame.font.init()
        self.h = h
        self.w = w

        self.font = pygame.font.Font(None, 24)
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        pygame.display.set_caption("Fly-in")
        self.fps = 60
        self.network: Network = network
        self.camera: Camera = Camera(Vector2(0, 0), 500, 0.5)

        self.drone_manager = drone_manager if drone_manager else DroneManager(
            network, find_all_paths(network)
        )
        self.renderer = Renderer(
            self.screen,
            self.camera,
            self.network,
            self.drone_manager,
            self.font)
        self.input_handler = InputHandler(self.camera)
        self.clock = pygame.time.Clock()

        self.is_paused: bool = False

    def running(self) -> None:
        """Runs the main loop until the window is closed.

        Controls: ``Esc`` or closing the window quits, ``Space`` or ``p``
        toggles the pause, ``r`` restarts the simulation, the arrow keys move
        the camera and ``w`` / ``s`` zoom in and out. Pygame is shut down
        when the loop ends.
        """
        run = True
        while run:
            dt = self.clock.tick(self.fps) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        run = False
                    elif event.key in (pygame.K_SPACE, pygame.K_p):
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_r:
                        self.drone_manager.start_simulation()
                        self.is_paused = False

            self.screen.fill(BG_COLOR)

            self.renderer.draw_connection()
            self.renderer.draw_nodes()

            if not self.is_paused:
                self.drone_manager.update_drones(dt)
                dir_cam = self.input_handler.get_direction()
                self.camera.update(self.screen, dir_cam, dt)

            self.renderer.draw_drone()

            self.renderer.draw_turn_info()

            if self.is_paused:
                pause_label = self.font.render(
                    "PAUSE (Appuyez sur ESPACE pour reprendre)",
                    True, Color("orange"))
                self.screen.blit(pause_label, (20, 90))

            self.input_handler.handle_input()
            pygame.display.update()
        pygame.quit()


def main() -> None:
    """Parses the command line and runs the simulation.

    Reads the map file given on the command line, builds the network and
    computes the schedule. With ``--visuel`` the pygame window is opened;
    otherwise the schedule is printed in the terminal. The ``--capacity``
    option is accepted but currently has no effect.
    """
    parser = argparse.ArgumentParser(
        description="Fly-in : simulation de drones")
    parser.add_argument("map_file", help="Fichier de carte .gph")
    parser.add_argument(
        "--visuel",
        action="store_true",
        help="Ouvre l'affichage visuel pygame (sans sortie texte)")
    parser.add_argument(
        "--capacity",
        action="store_true",
        help="update de l'affichage sur terminal"
    )
    args = parser.parse_args()

    net = NetworkParser(args.map_file).parse()
    paths = find_all_paths(net)

    drone_manager = DroneManager(net, paths)

    if args.visuel:
        interface = Interface(network=net, drone_manager=drone_manager)
        interface.running()
    # elif args.capacity:
    #     drone_positions = {
    #         d.id_drone: net.start for d in drone_manager.drones}
    #     for round_idx in range(len(drone_manager.schedule)):
    #         line = drone_manager.format_round(round_idx, drone_positions)
    #         if line:
    #             print(line)
    else:
        drone_manager.print_schedule()


if __name__ == "__main__":
    main()
