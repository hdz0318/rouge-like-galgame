"""Visual transitions for scene changes."""

from __future__ import annotations

import pygame


class Transition:
    """Base class for screen transitions."""

    def __init__(self, duration_ms: int = 500) -> None:
        self.duration = duration_ms
        self.elapsed = 0
        self.done = False

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration) if self.duration > 0 else 1.0

    def update(self, dt_ms: int) -> None:
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            self.done = True

    def render(self, screen: pygame.Surface, old: pygame.Surface | None, new: pygame.Surface | None) -> None:
        raise NotImplementedError


class FadeTransition(Transition):
    """Simple fade to black, then fade in."""

    def render(self, screen: pygame.Surface, old: pygame.Surface | None, new: pygame.Surface | None) -> None:
        p = self.progress
        if p < 0.5:
            # Fade out old
            alpha = int(255 * (p * 2))
            if old:
                screen.blit(old, (0, 0))
            overlay = pygame.Surface(screen.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            screen.blit(overlay, (0, 0))
        else:
            # Fade in new
            alpha = int(255 * ((1.0 - p) * 2))
            if new:
                screen.blit(new, (0, 0))
            overlay = pygame.Surface(screen.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(alpha)
            screen.blit(overlay, (0, 0))


class FlashTransition(Transition):
    """White flash for dramatic CG reveals."""

    def __init__(self, duration_ms: int = 600) -> None:
        super().__init__(duration_ms)

    def render(self, screen: pygame.Surface, old: pygame.Surface | None, new: pygame.Surface | None) -> None:
        p = self.progress
        if p < 0.3:
            # Flash to white
            alpha = int(255 * (p / 0.3))
            if old:
                screen.blit(old, (0, 0))
            overlay = pygame.Surface(screen.get_size())
            overlay.fill((255, 255, 255))
            overlay.set_alpha(alpha)
            screen.blit(overlay, (0, 0))
        elif p < 0.5:
            screen.fill((255, 255, 255))
        else:
            # Fade from white to new
            alpha = int(255 * ((p - 0.5) / 0.5))
            if new:
                screen.blit(new, (0, 0))
            overlay = pygame.Surface(screen.get_size())
            overlay.fill((255, 255, 255))
            overlay.set_alpha(255 - alpha)
            screen.blit(overlay, (0, 0))
