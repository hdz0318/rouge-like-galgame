"""HUD — top scene badge and lightweight route status."""

from __future__ import annotations

import pygame

from phantom_seed.ui.fonts import get_font


class HUD:
    """Renders a compact top-left location badge."""

    def __init__(self, screen_width: int) -> None:
        self.x = 18
        self.y = 14
        self.font: pygame.font.Font | None = None
        self.small_font: pygame.font.Font | None = None
        self._screen_width = screen_width

    def _ensure_font(self) -> None:
        if self.font is None:
            self.font = get_font(18, bold=True)
            self.small_font = get_font(14)

    def render(
        self,
        screen: pygame.Surface,
        affection: int,
        heroine_name: str = "",
        route_phase: str = "",
        *,
        chapter_beat: str = "",
        relationship_stage: str = "",
        location_label: str = "",
    ) -> None:
        self._ensure_font()
        assert self.font is not None

        location = location_label or "未命名场景"
        self._render_location_badge(screen, location)

    def _render_location_badge(self, screen: pygame.Surface, location: str) -> None:
        assert self.font is not None
        label = location
        text = self.font.render(label, True, (246, 232, 238))
        width = text.get_width() + 34
        height = 38
        badge = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(
            badge,
            (58, 38, 52, 214),
            [(12, 0), (width - 22, 0), (width, height // 2), (width - 22, height), (12, height), (0, height // 2)],
        )
        pygame.draw.polygon(
            badge,
            (210, 175, 195, 220),
            [(12, 1), (width - 23, 1), (width - 1, height // 2), (width - 23, height - 1), (12, height - 1), (1, height // 2)],
            2,
        )
        screen.blit(badge, (self.x, self.y))
        screen.blit(text, (self.x + 16, self.y + 8))
