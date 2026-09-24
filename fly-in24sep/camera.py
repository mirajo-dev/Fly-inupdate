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
    """Represents a 2D camera with movement and zoom.

    The camera stores a position in world space and a zoom factor. It
    provides the operations needed to move the view and to convert a
    world position into a screen position.

    Attributes:
        position: Current position of the camera in world space.
        speed: Movement speed of the camera in units per second.
        zoom: Scale factor applied to transformed positions.
    """

    def __init__(
            self, position: Vector2 | None = None,
            speed: float = 300.0, zoom: float = 1.0) -> None:
        """Initializes a 2D camera.

        Args:
            position: Initial position of the camera. ``None`` uses the
                origin.
            speed: Movement speed of the camera, in units per second.
            zoom: Initial zoom factor.
        """
        self.position = position if position is not None else Vector2(0, 0)
        self.speed = speed
        self.zoom = zoom

    def update(self, screen: Surface, direction: Vector2, dt: float) -> None:
        """Updates the camera position from a direction.

        The direction is normalized when it is not the zero vector, so that
        diagonal movement is not faster than horizontal or vertical
        movement.

        Args:
            screen: Display surface provided for compatibility with the
                caller. It is not used by this method.
            direction: Vector indicating the direction of movement.
            dt: Time elapsed since the last frame, in seconds.
        """
        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.position += direction * self.speed * dt

    def apply(self, point: Vector2) -> Vector2:
        """Transforms a world position into a screen position.

        The camera position is subtracted from the point, then the result is
        multiplied by the zoom factor.

        Args:
            point: Position in world space.

        Returns:
            Transformed position as a ``pygame.Vector2``.
        """
        return (point - self.position) * self.zoom

    def set_zoom(self, zoom: float) -> None:
        """Sets the zoom factor of the camera.

        Args:
            zoom: New zoom factor. Bounds validation, if needed, is the
                responsibility of the caller.
        """
        self.zoom = zoom

    def get_zoom(self) -> float:
        """Returns the current zoom factor.

        Returns:
            Current zoom value.
        """
        return self.zoom
