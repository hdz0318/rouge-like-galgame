"""Centralized font management for CJK text rendering."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

log = logging.getLogger(__name__)

# Preferred fonts in order — first available wins
_CJK_FONT_NAMES = [
    "microsoftyahei",     # 微软雅黑 (Windows)
    "microsoftyaheibold",
    "msyh",               # msyh.ttc
    "simhei",             # 黑体
    "simsun",             # 宋体
    "notoserif",          # Noto (Linux)
    "notosanssc",
    "wenquanyimicrohei",  # Linux fallback
    "arialUnicode",       # macOS
]

_resolved_path: str | None = None


def _find_cjk_font() -> str | None:
    """Find the first available CJK system font path."""
    global _resolved_path
    if _resolved_path is not None:
        return _resolved_path

    # Try pygame's SysFont name matching
    available = pygame.font.get_fonts()
    for name in _CJK_FONT_NAMES:
        if name.lower().replace(" ", "") in available:
            path = pygame.font.match_font(name)
            if path:
                _resolved_path = path
                log.info("Using CJK font: %s (%s)", name, path)
                return path

    # Direct path fallback for Windows
    for candidate in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]:
        if Path(candidate).exists():
            _resolved_path = candidate
            log.info("Using CJK font file: %s", candidate)
            return candidate

    log.warning("No CJK font found, falling back to pygame default")
    return None


def get_font(size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Get a font that supports Chinese characters."""
    path = _find_cjk_font()
    if path:
        try:
            font = pygame.font.Font(path, size)
            font.bold = bold
            font.italic = italic
            return font
        except Exception:
            log.exception("Failed to load font: %s", path)

    return pygame.font.SysFont("arial", size, bold=bold, italic=italic)
