"""HUD — top-left scene label."""

from __future__ import annotations

import pygame

from phantom_seed.ui.fonts import get_font


class HUD:
    """Renders the top-left scene label."""

    def __init__(self, screen_width: int) -> None:
        self.x = 20
        self.y = 16
        self.spacing = 8
        self.font: pygame.font.Font | None = None
        self._screen_width = screen_width

    def _ensure_font(self) -> None:
        if self.font is None:
            self.font = get_font(16)

    def render(
        self,
        screen: pygame.Surface,
        affection: int,
        heroine_name: str = "",
        route_phase: str = "",
    ) -> None:
        self._ensure_font()
        assert self.font is not None

        if heroine_name:
            label = heroine_name
            if route_phase == "heroine_route":
                label = f"{heroine_name}线"
            text_w = self.font.size(label)[0]
            panel_w = text_w + 28
            panel_h = 28
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 140))
            screen.blit(panel, (self.x - 8, self.y - 4))
            name_surf = self.font.render(label, True, (255, 220, 235))
            screen.blit(name_surf, (self.x, self.y))
