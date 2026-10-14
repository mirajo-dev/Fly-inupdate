"""2D camera used by the Fly-in graphical interface.

The module exits with an error message if ``pygame`` is not installed.
"""

import sys

try:
    from pygame import Surface, Vector2
except ImportError:
    print("[Error] Missing 'pygame' module. ")
    print("Required installation: 'pip install pygame'")
    sys.exit(1)


class Camera:
    """Represents a 2D camera with movement, zoom and optional bounds.

    The camera stores a position in world space and a zoom factor. It
    provides the operations needed to move the view and to convert a
    world position into a screen position.

    Attributes:
        position: Current position of the camera in world space.
        speed: Movement speed of the camera in units per second.
        zoom: Scale factor applied to transformed positions.
        bounds: Box (top-left, bottom-right) in which the center of the
            view must stay, or ``None`` if the camera is not limited.
    """

    def __init__(
            self, position: Vector2 | None = None,
            speed: float = 300.0, zoom: float = 1.0) -> None:
        """Initialize a 2D camera.

        Args:
            position: Initial position of the camera. ``None`` uses the
                origin.
            speed: Movement speed of the camera, in units per second.
            zoom: Initial zoom factor.
        """
        self.position = position if position is not None else Vector2(0, 0)
        self.speed = speed
        self.zoom = zoom
        self.bounds: tuple[Vector2, Vector2] | None = None

    def update(self, screen: Surface, direction: Vector2, dt: float) -> None:
        """Update the camera position from a direction.

        The direction is normalized when it is not the zero vector, so that
        diagonal movement is not faster than horizontal or vertical
        movement. The position is then kept inside the bounds, if any.

        Args:
            screen: Display surface, used to know the size of the view.
            direction: Vector indicating the direction of movement.
            dt: Time elapsed since the last frame, in seconds.
        """
        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.position += direction * self.speed * dt
        self.clamp(screen.get_size())

    def apply(self, point: Vector2) -> Vector2:
        """Transform a world position into a screen position.

        The camera position is subtracted from the point, then the result is
        multiplied by the zoom factor.

        Args:
            point: Position in world space.

        Returns:
            Transformed position as a ``pygame.Vector2``.
        """
        return (point - self.position) * self.zoom

    def set_zoom(self, zoom: float) -> None:
        """Set the zoom factor of the camera.

        Args:
            zoom: New zoom factor. Bounds validation, if needed, is the
                responsibility of the caller.
        """
        self.zoom = zoom

    def get_zoom(self) -> float:
        """Return the current zoom factor.

        Returns:
            Current zoom value.
        """
        return self.zoom

    def center_on(
            self,
            world_pos: Vector2,
            screen_size: tuple[int, int]) -> None:
        """Center the view on a world position.

        Args:
            world_pos: World position to put in the middle of the screen.
            screen_size: Size of the screen, in pixels.
        """
        half_screen = Vector2(screen_size) / 2
        self.position = world_pos - half_screen / self.get_zoom()

    def set_bounds(self, top_left: Vector2, bottom_right: Vector2) -> None:
        """Limit the camera so its view center stays inside a box.

        Args:
            top_left: Top-left corner of the box, in world space.
            bottom_right: Bottom-right corner of the box, in world space.
        """
        self.bounds = (top_left, bottom_right)

    def clamp(self, screen_size: tuple[int, int]) -> None:
        """Keep the center of the view inside the bounds, if any.

        Args:
            screen_size: Size of the screen, in pixels.
        """
        if self.bounds is None:
            return
        top_left, bottom_right = self.bounds
        half_view = Vector2(screen_size) / (2 * self.zoom)
        center = self.position + half_view
        center.x = max(top_left.x, min(center.x, bottom_right.x))
        center.y = max(top_left.y, min(center.y, bottom_right.y))
        self.position = center - half_view
