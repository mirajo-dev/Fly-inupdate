"""Scheduling, text output and pygame rendering for the Fly-in simulation.

The module computes a turn-by-turn schedule that moves every drone from
the start zone to the end zone while respecting zone and connection
capacities. The schedule is either printed in the terminal or animated
in a pygame window (``--visuel``).

Usage:
    python3 display.py <map_file> [--visuel]

The module exits with an error message if ``pygame`` is not installed.
"""

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
    print(" Required installation: 'pip install pygame'")
    sys.exit(1)

BG_COLOR = Color(235, 240, 240)
PAUSE_COLOR = Color(200, 80, 0)


class Interface:
    """Orchestrate the pygame initialization and the main loop.

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
        """Initialize pygame, the window and the helper objects.

        The camera is limited to the area of the map and centered on it.

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

        self.drone_manager = (
            drone_manager if drone_manager else DroneManager(network))

        top_left, bottom_right = self.drone_manager.get_world_bounds()
        self.camera.set_bounds(top_left, bottom_right)
        self.camera.center_on(
            self.drone_manager.get_world_center(),
            self.screen.get_size())

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
        """Run the main loop until the window is closed.

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
                    "PAUSED (Press SPACE to resume)",
                    True, PAUSE_COLOR)
                self.screen.blit(pause_label, (20, 90))

            self.input_handler.handle_input()
            self.camera.clamp(self.screen.get_size())
            pygame.display.update()
        pygame.quit()


def main() -> None:
    """Parse the command line and runs the simulation.

    Reads the map file given on the command line, builds the network and
    computes the schedule. With ``--visuel`` the pygame window is opened;
    otherwise the schedule is printed in the terminal.
    """
    parser = argparse.ArgumentParser(
        description="Fly-in : simulation de drones")
    parser.add_argument("map_file", help="Fichier de carte .gph")
    parser.add_argument(
        "--visuel",
        action="store_true",
        help="Opens the Pygame visual display (without text output)")

    args = parser.parse_args()

    try:
        net = NetworkParser(args.map_file).parse()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    drone_manager = DroneManager(net)

    if args.visuel:
        interface = Interface(network=net, drone_manager=drone_manager)
        interface.running()
    else:
        drone_manager.print_schedule()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nexit")
