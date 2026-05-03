"""Dialogue box rendering with typewriter effect and VN controls."""

from __future__ import annotations

from pathlib import Path

import pygame

from phantom_seed.ui.assets import load_image
from phantom_seed.ui.fonts import get_font


class DialogueBox:
    """Renders the dialogue box at the bottom of the screen."""

    CONTROL_ACTIONS = [
        ("Q.SAVE", "qsave"),
        ("Q.LOAD", "qload"),
        ("SAVE", "save"),
        ("LOAD", "load"),
        ("AUTO", "auto"),
        ("SKIP", "skip"),
        ("LOG", "backlog"),
        ("CONFIG", "config"),
    ]

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_w = screen_width
        self.screen_h = screen_height

        self.margin = 32
        self.box_height = 206
        self.box_y = screen_height - self.box_height - 18
        self.box_w = screen_width - self.margin * 2
        self.portrait_size = 118

        self.name_font: pygame.font.Font | None = None
        self.text_font: pygame.font.Font | None = None
        self.mono_font: pygame.font.Font | None = None
        self.ctrl_font: pygame.font.Font | None = None

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
        self._control_rects: list[tuple[str, pygame.Rect]] = []
        self._hovered_action = ""

    def _ensure_fonts(self) -> None:
        if self.name_font is None:
            self.name_font = get_font(24, bold=True)
            self.text_font = get_font(21)
            self.mono_font = get_font(18, italic=True)
            self.ctrl_font = get_font(18)

    def set_dialogue(
        self,
        speaker: str,
        text: str,
        inner_monologue: str = "",
        portrait_path: str | Path | None = None,
    ) -> None:
        self.speaker = speaker
        self.full_text = text
        self.inner_text = inner_monologue
        self.char_index = 0
        self.tick_timer = 0
        self.finished = False
        self.portrait = self._load_portrait(portrait_path) if portrait_path else None

    def set_text_speed(self, ms: int) -> None:
        self.tick_interval_ms = max(0, ms)

    def skip(self) -> None:
        self.char_index = len(self.full_text)
        self.finished = True

    def handle_mouse_move(self, pos: tuple[int, int]) -> None:
        self._hovered_action = ""
        for action, rect in self._control_rects:
            if rect.collidepoint(pos):
                self._hovered_action = action
                return

    def action_at(self, pos: tuple[int, int]) -> str | None:
        for action, rect in self._control_rects:
            if rect.collidepoint(pos):
                return action
        return None

    def update(self, dt_ms: int) -> None:
        if self.finished:
            return
        if self.tick_interval_ms <= 0:
            self.skip()
            return
        self.tick_timer += dt_ms
        while self.tick_timer >= self.tick_interval_ms:
            self.tick_timer -= self.tick_interval_ms
            self.char_index = min(
                self.char_index + self.chars_per_tick,
                len(self.full_text),
            )
        if self.char_index >= len(self.full_text):
            self.finished = True

    def render(
        self,
        screen: pygame.Surface,
        *,
        auto_mode: bool = False,
        skip_mode: bool = False,
    ) -> None:
        self._ensure_fonts()
        assert self.text_font is not None
        assert self.name_font is not None
        assert self.mono_font is not None
        assert self.ctrl_font is not None

        self._render_back_panel(screen)

        text_x = self.margin + 28
        text_y = self.box_y + 34
        text_w = self.box_w - 56

        if self.portrait is not None:
            portrait_x = self.margin + 18
            portrait_y = self.box_y + 60
            self._render_portrait(screen, portrait_x, portrait_y)
            text_x += self.portrait_size + 24
            text_w -= self.portrait_size + 24

        if self.speaker:
            self._render_nameplate(screen, text_x)

        visible_text = self.full_text[: self.char_index]
        self._render_wrapped_text(
            screen,
            visible_text,
            self.text_font,
            (242, 236, 244),
            text_x,
            text_y,
            text_w,
        )

        if self.inner_text:
            inner_y = self.box_y + self.box_height - 60
            mono_text = f"({self.inner_text})"
            self._render_wrapped_text(
                screen,
                mono_text,
                self.mono_font,
                (204, 186, 212),
                text_x,
                inner_y,
                text_w,
            )

        self._render_controls(screen, auto_mode=auto_mode, skip_mode=skip_mode)
        self._render_advance_indicator(screen)

    def _render_back_panel(self, screen: pygame.Surface) -> None:
        panel = pygame.Surface((self.box_w, self.box_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 14, 26, 165), panel.get_rect(), border_radius=22)
        pygame.draw.rect(panel, (236, 197, 218, 210), panel.get_rect(), 2, border_radius=22)
        inner = panel.get_rect().inflate(-10, -10)
        pygame.draw.rect(panel, (76, 54, 74, 96), inner, 1, border_radius=18)
        gloss = pygame.Surface((self.box_w, 54), pygame.SRCALPHA)
        gloss.fill((255, 255, 255, 16))
        panel.blit(gloss, (0, 0))
        screen.blit(panel, (self.margin, self.box_y))

    def _render_portrait(self, screen: pygame.Surface, portrait_x: int, portrait_y: int) -> None:
        assert self.portrait is not None
        frame = pygame.Surface(
            (self.portrait_size + 12, self.portrait_size + 12),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(frame, (250, 224, 235, 240), frame.get_rect(), border_radius=18)
        pygame.draw.rect(
            frame,
            (115, 78, 110, 220),
            frame.get_rect().inflate(-4, -4),
            border_radius=16,
        )
        inner = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        pygame.draw.rect(inner, (28, 20, 30, 245), inner.get_rect(), border_radius=14)
        inner.blit(self.portrait, (0, 0))
        frame.blit(inner, (6, 6))
        screen.blit(frame, (portrait_x - 6, portrait_y - 6))

    def _render_nameplate(self, screen: pygame.Surface, text_x: int) -> None:
        assert self.name_font is not None
        label_w = max(182, self.name_font.size(self.speaker)[0] + 72)
        name_bg = pygame.Surface((label_w, 38), pygame.SRCALPHA)
        pygame.draw.rect(name_bg, (255, 241, 248, 230), name_bg.get_rect(), border_radius=14)
        pygame.draw.rect(name_bg, (235, 178, 205, 245), name_bg.get_rect(), 2, border_radius=14)
        screen.blit(name_bg, (text_x - 10, self.box_y - 16))
        name_surf = self.name_font.render(self.speaker, True, (120, 66, 105))
        screen.blit(name_surf, (text_x + 10, self.box_y - 10))
        blossom = self.name_font.render("✿", True, (236, 132, 188))
        screen.blit(blossom, (text_x + label_w - 40, self.box_y - 11))

    def _render_controls(
        self,
        screen: pygame.Surface,
        *,
        auto_mode: bool,
        skip_mode: bool,
    ) -> None:
        assert self.ctrl_font is not None
        self._control_rects = []
        btn_w = 96
        btn_h = 34
        spacing = 4
        total_w = len(self.CONTROL_ACTIONS) * btn_w + (len(self.CONTROL_ACTIONS) - 1) * spacing
        start_x = (self.screen_w - total_w) // 2
        y = self.box_y + self.box_height - 18

        for index, (label, action) in enumerate(self.CONTROL_ACTIONS):
            rect = pygame.Rect(start_x + index * (btn_w + spacing), y, btn_w, btn_h)
            self._control_rects.append((action, rect))
            is_hover = self._hovered_action == action
            is_active = (action == "auto" and auto_mode) or (action == "skip" and skip_mode)
            fill = (140, 95, 132, 235) if is_active else (84, 60, 82, 205)
            if is_hover:
                fill = (168, 118, 154, 235)
            btn = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(btn, fill, btn.get_rect(), border_radius=10)
            pygame.draw.rect(
                btn,
                (242, 207, 222, 245) if (is_hover or is_active) else (174, 143, 168, 220),
                btn.get_rect(),
                1,
                border_radius=10,
            )
            screen.blit(btn, rect.topleft)
            text_color = (255, 244, 248) if (is_hover or is_active) else (224, 210, 221)
            text = self.ctrl_font.render(label, True, text_color)
            screen.blit(
                text,
                (rect.x + (rect.w - text.get_width()) // 2, rect.y + 6),
            )

    def _render_advance_indicator(self, screen: pygame.Surface) -> None:
        tick = pygame.time.get_ticks()
        if not self.finished:
            dot_alpha = 86 + int(((tick // 120) % 4) * 22)
            glow = pygame.Surface((16, 16), pygame.SRCALPHA)
            pygame.draw.circle(glow, (248, 218, 232, dot_alpha), (8, 8), 5)
            screen.blit(glow, (self.margin + self.box_w - 34, self.box_y + self.box_height - 46))
            return
        if (tick // 420) % 2 == 0:
            blossom = self.name_font.render("✿", True, (250, 220, 236))
            screen.blit(
                blossom,
                (self.margin + self.box_w - 38, self.box_y + self.box_height - 56),
            )

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
            return pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        head_h = max(int(bbox.height * 0.30), self.portrait_size)
        crop_w = max(int(bbox.width * 0.50), self.portrait_size)
        crop_x = max(bbox.x + (bbox.width - crop_w) // 2, 0)
        crop_y = max(bbox.y - int(bbox.height * 0.03), 0)
        crop_w = min(crop_w, surface.get_width() - crop_x)
        crop_h = min(head_h, surface.get_height() - crop_y)
        portrait_rect = pygame.Rect(crop_x, crop_y, crop_w, crop_h)
        cropped = pygame.Surface((crop_w, crop_h), pygame.SRCALPHA)
        cropped.blit(surface, (0, 0), portrait_rect)

        scale = max(self.portrait_size / crop_w, self.portrait_size / crop_h)
        scaled = pygame.transform.smoothscale(
            cropped,
            (max(1, int(crop_w * scale)), max(1, int(crop_h * scale))),
        )
        output = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        x = (self.portrait_size - scaled.get_width()) // 2
        y = min(0, (self.portrait_size - scaled.get_height()) // 2 - 6)
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
        line_height = font.get_linesize() + 4
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
