"""Choice menu rendering."""

from __future__ import annotations

import pygame

from phantom_seed.ai.protocol import Choice
from phantom_seed.ui.fonts import get_font


class ChoiceMenu:
    """Renders interactive choice buttons."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_w = screen_width
        self.screen_h = screen_height
        self.font: pygame.font.Font | None = None
        self.hint_font: pygame.font.Font | None = None
        self.choices: list[Choice] = []
        self.hovered: int = -1
        self.selected: int = -1
        self._rects: list[pygame.Rect] = []
        self.visible = False

    def _ensure_font(self) -> None:
        if self.font is None:
            self.font = get_font(24)
            self.hint_font = get_font(15)

    def show(self, choices: list[Choice]) -> None:
        self.choices = choices
        self.hovered = -1
        self.selected = -1
        self.visible = True
        self._build_rects()

    def hide(self) -> None:
        self.visible = False
        self.choices = []
        self._rects = []

    def _build_rects(self) -> None:
        self._ensure_font()
        btn_w = min(720, self.screen_w - 220)
        btn_h = 68
        spacing = 16
        total_h = len(self.choices) * btn_h + (len(self.choices) - 1) * spacing
        start_y = self.screen_h // 2 - total_h // 2 - 10
        start_x = (self.screen_w - btn_w) // 2

        self._rects = []
        for i in range(len(self.choices)):
            y = start_y + i * (btn_h + spacing)
            self._rects.append(pygame.Rect(start_x, y, btn_w, btn_h))

    def handle_mouse_move(self, pos: tuple[int, int]) -> None:
        if not self.visible:
            return
        self.hovered = -1
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                self.hovered = i
                break

    def handle_click(self, pos: tuple[int, int]) -> Choice | None:
        if not self.visible:
            return None
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                self.selected = i
                return self.choices[i]
        return None

    def render(self, screen: pygame.Surface) -> None:
        if not self.visible or not self.choices:
            return
        self._ensure_font()
        assert self.font is not None
        assert self.hint_font is not None

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((16, 10, 18, 112))
        screen.blit(overlay, (0, 0))

        title = self.hint_font.render("请选择接下来的行动方向", True, (244, 228, 236))
        screen.blit(title, ((self.screen_w - title.get_width()) // 2, self._rects[0].y - 38))

        for i, (choice, rect) in enumerate(zip(self.choices, self._rects)):
            is_hover = i == self.hovered
            number = self.hint_font.render(str(i + 1), True, (255, 246, 250))

            panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            fill = (126, 82, 108, 228) if is_hover else (70, 46, 63, 212)
            border = (255, 221, 233) if is_hover else (190, 152, 173)
            pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=18)
            pygame.draw.rect(panel, border, panel.get_rect(), 2 if is_hover else 1, border_radius=18)
            gloss = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 12))
            panel.blit(gloss, (0, 0))
            screen.blit(panel, rect.topleft)

            bubble = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (237, 170, 200, 230), (16, 16), 16)
            screen.blit(bubble, (rect.x + 18, rect.y + 18))
            screen.blit(number, (rect.x + 12 + (32 - number.get_width()) // 2, rect.y + 7))

            text = self.font.render(choice.text, True, (255, 243, 248) if is_hover else (238, 227, 236))
            screen.blit(text, (rect.x + 66, rect.y + 18))
