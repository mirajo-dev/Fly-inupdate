import sys

try:
    from pygame import Surface, Vector2
except ImportError:
    print("[Error] Missing 'pygame' module. Required installation: 'pip install pygame'")
    sys.exit(1)


class Camera:
    """Représente une caméra 2D avec déplacement et zoom.

La caméra stocke une position dans l'espace du monde et un facteur de zoom.
Elle fournit les opérations nécessaires pour déplacer la vue et convertir une
position du monde en position écran.

Attributes:
    position: Position actuelle de la caméra dans l'espace du monde.
    speed: Vitesse de déplacement de la caméra en unités par seconde.
    zoom: Facteur d'échelle appliqué aux positions transformées.
"""
    def __init__(self, position: Vector2 = None, speed: float = 300.0, zoom: float = 1.0):
        """Initialise une caméra 2D.

Args:
    position: Position initiale de la caméra. ``None`` utilise l'origine.
    speed: Vitesse de déplacement de la caméra.
    zoom: Facteur de zoom initial.
"""
        self.position = position if position is not None else Vector2(0, 0)
        self.speed = speed
        self.zoom = zoom

    def update(self, screen: Surface, direction: Vector2, dt: float) -> None:
        """Met à jour la position de la caméra à partir d'une direction.

La direction est normalisée lorsqu'elle est non nulle afin que le déplacement
diagonal ne soit pas plus rapide que le déplacement horizontal ou vertical.

Args:
    screen: Surface d'affichage fournie pour compatibilité avec l'appelant. Elle
        n'est pas utilisée directement par la méthode.
    direction: Vecteur indiquant la direction du déplacement.
    dt: Temps écoulé depuis la dernière frame, en secondes.

Returns:
    ``None``.
"""
        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.position += direction * self.speed * dt

    def apply(self, point: Vector2) -> Vector2:
        """Transforme une position du monde en position relative à l'écran.

La position de la caméra est soustraite du point, puis le résultat est multiplié
par le facteur de zoom.

Args:
    point: Position dans l'espace du monde.

Returns:
    Position transformée sous forme de ``pygame.Vector2``.
"""
        return (point - self.position) * self.zoom

    def set_zoom(self, zoom: float):
        """Définit directement le facteur de zoom de la caméra.

Args:
    zoom: Nouveau facteur de zoom. La validation des limites, si nécessaire, est
        assurée par l'appelant.

Returns:
    ``None``.
"""
        self.zoom = zoom

    def get_zoom(self) -> float:
        """Retourne le facteur de zoom courant.

Returns:
    Valeur du zoom sous forme de ``float``.
"""
        return self.zoom