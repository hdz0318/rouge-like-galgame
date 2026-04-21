"""Dialogue box rendering with typewriter effect."""

from __future__ import annotations

from pathlib import Path

import pygame

from phantom_seed.ui.assets import load_image
from phantom_seed.ui.fonts import get_font


class DialogueBox:
    """Renders the dialogue box at the bottom of the screen."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_w = screen_width
        self.screen_h = screen_height

        # Box dimensions
        self.margin = 40
        self.box_height = 200
        self.box_y = screen_height - self.box_height - 20
        self.box_w = screen_width - self.margin * 2
        self.portrait_size = 116

        # Text
        self.name_font: pygame.font.Font | None = None
        self.text_font: pygame.font.Font | None = None
        self.mono_font: pygame.font.Font | None = None

        # Typewriter state
        self.full_text = ""
        self.inner_text = ""
        self.speaker = ""
        self.char_index = 0
        self.chars_per_tick = 1
        self.tick_timer = 0
        self.tick_interval_ms = 30
        self.finished = False
        self.portrait: pygame.Surface | None = None
        self._portrait_cache: dict[str, pygame.Surface | None] = {}

    def _ensure_fonts(self) -> None:
        if self.name_font is None:
            self.name_font = get_font(22, bold=True)
            self.text_font = get_font(20)
            self.mono_font = get_font(18, italic=True)

    def set_dialogue(
        self,
        speaker: str,
        text: str,
        inner_monologue: str = "",
        portrait_path: str | Path | None = None,
    ) -> None:
        """Set new dialogue to display with typewriter effect."""
        self.speaker = speaker
        self.full_text = text
        self.inner_text = inner_monologue
        self.char_index = 0
        self.tick_timer = 0
        self.finished = False
        self.portrait = self._load_portrait(portrait_path) if portrait_path else None

    def set_text_speed(self, ms: int) -> None:
        """Set the typewriter tick interval in milliseconds. 0 = instant."""
        self.tick_interval_ms = ms

    def skip(self) -> None:
        """Skip typewriter and show full text immediately."""
        self.char_index = len(self.full_text)
        self.finished = True

    def update(self, dt_ms: int) -> None:
        """Advance the typewriter effect."""
        if self.finished:
            return
        self.tick_timer += dt_ms
        while self.tick_timer >= self.tick_interval_ms:
            self.tick_timer -= self.tick_interval_ms
            self.char_index = min(
                self.char_index + self.chars_per_tick, len(self.full_text)
            )
        if self.char_index >= len(self.full_text):
            self.finished = True

    def render(self, screen: pygame.Surface) -> None:
        self._ensure_fonts()
        assert self.text_font is not None
        assert self.name_font is not None
        assert self.mono_font is not None

        # Semi-transparent box
        box_surf = pygame.Surface((self.box_w, self.box_height), pygame.SRCALPHA)
        box_surf.fill((45, 35, 50, 200))
        pygame.draw.rect(
            box_surf, (180, 140, 170, 180), (0, 0, self.box_w, self.box_height), 2
        )
        screen.blit(box_surf, (self.margin, self.box_y))

        text_x = self.margin + 24
        text_y = self.box_y + 24
        text_w = self.box_w - 48

        if self.portrait is not None:
            portrait_x = self.margin + 18
            portrait_y = self.box_y + 42
            frame = pygame.Surface(
                (self.portrait_size + 8, self.portrait_size + 8),
                pygame.SRCALPHA,
            )
            frame.fill((92, 60, 82, 220))
            pygame.draw.rect(
                frame,
                (225, 186, 204, 235),
                (0, 0, self.portrait_size + 8, self.portrait_size + 8),
                border_radius=18,
            )
            inner = pygame.Surface(
                (self.portrait_size, self.portrait_size),
                pygame.SRCALPHA,
            )
            inner.fill((26, 18, 28, 230))
            inner.blit(self.portrait, (0, 0))
            frame.blit(inner, (4, 4))
            screen.blit(frame, (portrait_x - 4, portrait_y - 4))
            text_x += self.portrait_size + 18
            text_w -= self.portrait_size + 18

        # Speaker name
        if self.speaker:
            name_bg = pygame.Surface((len(self.speaker) * 20 + 24, 30), pygame.SRCALPHA)
            name_bg.fill((80, 50, 70, 220))
            screen.blit(name_bg, (text_x - 8, self.box_y - 15))

            name_surf = self.name_font.render(self.speaker, True, (255, 210, 230))
            screen.blit(name_surf, (text_x + 4, self.box_y - 12))

        # Main text (typewriter)
        visible_text = self.full_text[: self.char_index]
        self._render_wrapped_text(
            screen,
            visible_text,
            self.text_font,
            (230, 230, 240),
            text_x,
            text_y,
            text_w,
        )

        # Click indicator
        if self.finished:
            indicator_x = self.margin + self.box_w - 40
            indicator_y = self.box_y + self.box_height - 30
            tick = pygame.time.get_ticks()
            if (tick // 500) % 2 == 0:
                points = [
                    (indicator_x, indicator_y),
                    (indicator_x + 12, indicator_y + 8),
                    (indicator_x + 24, indicator_y),
                ]
                pygame.draw.polygon(screen, (200, 200, 220), points)

    def _load_portrait(self, portrait_path: str | Path) -> pygame.Surface | None:
        key = str(portrait_path)
        if key in self._portrait_cache:
            return self._portrait_cache[key]
        surface = load_image(portrait_path)
        if surface is None:
            self._portrait_cache[key] = None
            return None
        portrait = self._extract_head_portrait(surface)
        self._portrait_cache[key] = portrait
        return portrait

    def _extract_head_portrait(self, surface: pygame.Surface) -> pygame.Surface:
        bbox = surface.get_bounding_rect(min_alpha=8)
        if bbox.width <= 0 or bbox.height <= 0:
            fallback = pygame.Surface(
                (self.portrait_size, self.portrait_size),
                pygame.SRCALPHA,
            )
            return fallback
        head_h = max(int(bbox.height * 0.42), self.portrait_size)
        crop_w = max(int(bbox.width * 0.58), self.portrait_size)
        crop_x = max(bbox.x + (bbox.width - crop_w) // 2, 0)
        crop_y = max(bbox.y, 0)
        crop_w = min(crop_w, surface.get_width() - crop_x)
        crop_h = min(head_h, surface.get_height() - crop_y)
        portrait_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
        cropped = pygame.Surface((crop_w, crop_h), pygame.SRCALPHA)
        cropped.blit(surface, (0, 0), portrait_rect)

        scale = max(self.portrait_size / crop_w, self.portrait_size / crop_h)
        scaled = pygame.transform.smoothscale(
            cropped,
            (
                max(1, int(crop_w * scale)),
                max(1, int(crop_h * scale)),
            ),
        )
        output = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        x = (self.portrait_size - scaled.get_width()) // 2
        y = (self.portrait_size - scaled.get_height()) // 2
        output.blit(scaled, (x, y))
        return output

    def _render_wrapped_text(
        self,
        screen: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
    ) -> None:
        """Render text with word wrapping (handles CJK characters)."""
        line_height = font.get_linesize() + 2
        current_x = x
        current_y = y

        for char in text:
            char_surf = font.render(char, True, color)
            char_w = char_surf.get_width()

            if char == "\n":
                current_x = x
                current_y += line_height
                continue

            if current_x + char_w > x + max_width:
                current_x = x
                current_y += line_height

            screen.blit(char_surf, (current_x, current_y))
            current_x += char_w
