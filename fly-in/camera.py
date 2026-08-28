import pygame
from pygame import Surface, Vector2


class Camera:
    def __init__(self, position: Vector2 = None, speed: float = 300.0, zoom: float = 1.0):
        self.position = position if position is not None else Vector2(0, 0)
        self.speed = speed
        self.zoom = zoom

    def update(self, screen: Surface, direction: Vector2, dt: float) -> None:
        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.position += direction * self.speed * dt

    def apply(self, point: Vector2) -> Vector2:
        return (point - self.position) * self.zoom

    def set_zoom(self, zoom: float):
        self.zoom = zoom

    def get_zoom(self) -> float:
        return self.zoom