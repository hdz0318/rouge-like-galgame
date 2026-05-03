"""Main menu UI for Phantom Seed."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from phantom_seed.ui.fonts import get_font

if TYPE_CHECKING:
    from phantom_seed.core.save_system import SaveSystem


class MainMenu:
    """Renders the main menu with a visual novel style presentation."""

    BUTTONS = [
        ("开始游戏", "new_game"),
        ("继续游戏", "continue"),
        ("读取存档", "load"),
        ("设置", "settings"),
        ("退出", "exit"),
    ]

    def __init__(self, screen_w: int, screen_h: int, save_system: SaveSystem) -> None:
        self.sw = screen_w
        self.sh = screen_h
        self.save_system = save_system

        self._title_font: pygame.font.Font | None = None
        self._btn_font: pygame.font.Font | None = None
        self._hint_font: pygame.font.Font | None = None
        self._sub_font: pygame.font.Font | None = None

        self._rects: list[pygame.Rect] = []
        self._hovered = -1

    def _ensure_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = get_font(58, bold=True)
            self._btn_font = get_font(24)
            self._hint_font = get_font(16)
            self._sub_font = get_font(20)

    def _has_quick_save(self) -> bool:
        return self.save_system.slot_info("QUICK") is not None

    def _build_rects(self) -> None:
        btn_w, btn_h = 300, 52
        spacing = 16
        total_h = len(self.BUTTONS) * btn_h + (len(self.BUTTONS) - 1) * spacing
        start_y = max(220, (self.sh - total_h) // 2 + 64)
        start_x = self.sw - btn_w - 94
        self._rects = [
            pygame.Rect(start_x, start_y + i * (btn_h + spacing), btn_w, btn_h)
            for i in range(len(self.BUTTONS))
        ]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if not self._rects:
            self._build_rects()

        if event.type == pygame.MOUSEMOTION:
            self._hovered = -1
            for i, rect in enumerate(self._rects):
                if rect.collidepoint(event.pos):
                    self._hovered = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._rects):
                if rect.collidepoint(event.pos):
                    action = self.BUTTONS[i][1]
                    if action == "continue" and not self._has_quick_save():
                        return None
                    return action
        return None

    def render(self, screen: pygame.Surface) -> None:
        self._ensure_fonts()
        assert self._title_font is not None
        assert self._btn_font is not None
        assert self._hint_font is not None
        assert self._sub_font is not None

        if not self._rects:
            self._build_rects()

        self._render_background(screen)

        title = self._title_font.render("Phantom Seed", True, (255, 242, 248))
        screen.blit(title, (88, 96))
        subtitle = self._sub_font.render("命运的种子，在恋爱与选择中发芽", True, (230, 208, 220))
        screen.blit(subtitle, (96, 172))

        info_panel = pygame.Surface((480, 138), pygame.SRCALPHA)
        pygame.draw.rect(info_panel, (40, 24, 34, 168), info_panel.get_rect(), border_radius=26)
        pygame.draw.rect(info_panel, (220, 180, 199, 210), info_panel.get_rect(), 1, border_radius=26)
        screen.blit(info_panel, (84, 238))
        lines = [
            "AI 生成女主、剧情与场景立绘",
            "多路线推进，自动承接伏笔与关系变化",
            "支持快速存读档、回放日志与自动播放",
        ]
        for idx, line in enumerate(lines):
            surf = self._hint_font.render(f"✦ {line}", True, (241, 228, 235))
            screen.blit(surf, (110, 268 + idx * 32))

        has_quick = self._has_quick_save()
        quick_text = "检测到快速存档，可直接继续" if has_quick else "暂无快速存档，先开始一局新的邂逅吧"
        quick_surf = self._hint_font.render(quick_text, True, (215, 193, 206))
        screen.blit(quick_surf, (96, self.sh - 66))

        for i, ((label, action), rect) in enumerate(zip(self.BUTTONS, self._rects)):
            is_hover = i == self._hovered
            disabled = action == "continue" and not has_quick
            self._render_button(screen, rect, label, is_hover=is_hover, disabled=disabled)

    def _render_background(self, screen: pygame.Surface) -> None:
        base = pygame.Surface((self.sw, self.sh))
        base.fill((28, 16, 22))
        for y in range(self.sh):
            ratio = y / max(1, self.sh - 1)
            color = (
                int(42 + ratio * 36),
                int(24 + ratio * 22),
                int(38 + ratio * 42),
            )
            pygame.draw.line(base, color, (0, y), (self.sw, y))
        screen.blit(base, (0, 0))

        glow = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 210, 220, 26), (200, 120), 180)
        pygame.draw.circle(glow, (244, 170, 206, 30), (self.sw - 180, 210), 260)
        pygame.draw.circle(glow, (222, 145, 194, 18), (self.sw // 2, self.sh - 120), 320)
        screen.blit(glow, (0, 0))

        frame = pygame.Rect(26, 24, self.sw - 52, self.sh - 48)
        pygame.draw.rect(screen, (226, 184, 204, 120), frame, 1, border_radius=18)

    def _render_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        *,
        is_hover: bool,
        disabled: bool,
    ) -> None:
        assert self._btn_font is not None

        if disabled:
            fill = (68, 46, 56, 178)
            border = (108, 88, 96)
            text_color = (136, 122, 130)
        elif is_hover:
            fill = (180, 108, 144, 228)
            border = (255, 214, 230)
            text_color = (255, 247, 250)
        else:
            fill = (100, 62, 82, 214)
            border = (208, 166, 188)
            text_color = (247, 234, 240)

        btn = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(btn, fill, btn.get_rect(), border_radius=16)
        pygame.draw.rect(btn, border, btn.get_rect(), 2 if is_hover else 1, border_radius=16)
        highlight = pygame.Surface((rect.w, rect.h // 2), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 12 if not disabled else 5))
        btn.blit(highlight, (0, 0))
        screen.blit(btn, rect.topleft)

        text = self._btn_font.render(label, True, text_color)
        screen.blit(
            text,
            (rect.x + (rect.w - text.get_width()) // 2, rect.y + 11),
        )
