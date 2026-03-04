"""Dynamic asset loader and cache for Pygame surfaces."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

log = logging.getLogger(__name__)

# Module-level cache: path string -> pygame.Surface
_surface_cache: dict[str, pygame.Surface] = {}


def load_image(path: str | Path, target_size: tuple[int, int] | None = None) -> pygame.Surface | None:
    """Load an image file as a Pygame surface, with caching.

    Args:
        path: Path to the image file.
        target_size: If given, scale the surface to this (width, height).

    Returns:
        The loaded surface, or None if loading failed.
    """
    key = f"{path}_{target_size}"
    if key in _surface_cache:
        return _surface_cache[key]

    p = Path(path)
    if not p.exists():
        log.warning("Image not found: %s", p)
        return None

    try:
        surface = pygame.image.load(str(p)).convert_alpha()
        if target_size:
            surface = pygame.transform.smoothscale(surface, target_size)
        _surface_cache[key] = surface
        return surface
    except Exception:
        log.exception("Failed to load image: %s", p)
        return None


def create_placeholder(width: int, height: int, color: tuple[int, int, int] = (40, 40, 60)) -> pygame.Surface:
    """Create a solid-color placeholder surface."""
    surf = pygame.Surface((width, height))
    surf.fill(color)
    return surf


def clear_cache() -> None:
    """Clear the surface cache (e.g., on new game)."""
    _surface_cache.clear()
