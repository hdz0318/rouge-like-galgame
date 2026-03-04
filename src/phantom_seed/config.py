"""Configuration and settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env file from project root into os.environ."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


# Load .env on import
_load_dotenv()


@dataclass
class Config:
    """Global configuration for Phantom Seed."""

    # Paths
    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )
    assets_dir: Path = field(init=False)
    cache_dir: Path = field(init=False)

    # Window
    screen_width: int = 1280
    screen_height: int = 720
    fps: int = 60
    title: str = "Phantom Seed"

    # OpenRouter API
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "")
    )
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    text_model: str = "google/gemini-3-flash-preview"
    image_model: str = "google/gemini-3.1-flash-image-preview"

    # Game defaults
    initial_sanity: int = 100
    initial_affection: int = 0

    # Generation
    prefetch_count: int = 1
    generation_timeout: float = 30.0

    def __post_init__(self) -> None:
        self.assets_dir = self.project_root / "assets"
        self.cache_dir = self.project_root / ".cache" / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
