"""OpenRouter image client for image generation and editing-style workflows."""

from __future__ import annotations

import hashlib
import io
import logging
import threading
from collections import deque
from base64 import b64decode
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from phantom_seed.ai.llm import OpenRouterClient
from phantom_seed.ai.prompts.visual import (
    BACKGROUND_PROMPT_TEMPLATE,
    CG_PROMPT_TEMPLATE,
    VISUAL_PROMPT_TEMPLATE,
)

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)


class ImagenClient:
    """OpenRouter image client with optional visual-reference inputs."""

    _SPRITE_CANVAS = (1024, 1536)
    _SPRITE_FOOT_MARGIN = 36
    _SPRITE_SIDE_MARGIN_RATIO = 0.08
    _ALPHA_THRESHOLD = 16
    _REMBG_SESSION = None
    _REMBG_INIT_LOCK = threading.Lock()

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = OpenRouterClient(config.openrouter_api_key)
        self.model = config.image_model
        self.promo_model = config.promo_image_model
        self.cache_dir = config.cache_dir

    def _cache_path(self, prompt: str) -> Path:
        h = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return self.cache_dir / f"{h}.png"

    def _request_image(
        self,
        model: str,
        full_prompt: str,
        *,
        references: list[Path] | None = None,
        aspect_ratio: str = "2:3",
    ) -> Image.Image | None:
        """Send an image request and return a PIL Image or None."""
        data_url = self.client.image_generation(
            model=model,
            prompt=full_prompt,
            references=references,
            aspect_ratio=aspect_ratio,
        )
        _, b64_data = data_url.split(",", 1)
        return Image.open(io.BytesIO(b64decode(b64_data))).convert("RGBA")

    @staticmethod
    def _remove_white_bg(
        img: Image.Image, threshold: int = 240, tolerance: int = 30
    ) -> Image.Image:
        """Remove white/near-white background using corner flood-fill, returning RGBA image."""
        rgba = img.convert("RGBA")
        w, h = rgba.size
        pixels = rgba.load()

        # Determine background color by sampling the 4 corners
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        bg_samples = [pixels[x, y][:3] for x, y in corners]
        # Use the most common corner color as background reference
        from collections import Counter

        bg_color = Counter(
            tuple(min(255, max(0, c)) for c in s) for s in bg_samples
        ).most_common(1)[0][0]

        # Only run removal if background is light (likely white)
        if not all(c >= threshold for c in bg_color):
            return rgba

        visited = [[False] * h for _ in range(w)]
        queue: list[tuple[int, int]] = list(corners)
        for cx, cy in corners:
            visited[cx][cy] = True

        while queue:
            x, y = queue.pop()
            r, g, b, a = pixels[x, y]
            # Is this pixel close to the background color?
            if (
                abs(r - bg_color[0]) <= tolerance
                and abs(g - bg_color[1]) <= tolerance
                and abs(b - bg_color[2]) <= tolerance
            ):
                pixels[x, y] = (r, g, b, 0)  # make transparent
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                        visited[nx][ny] = True
                        queue.append((nx, ny))
        return rgba

    @staticmethod
    def _remove_background(img: Image.Image) -> Image.Image:
        """Prefer rembg matting and fall back to simple white-bg removal."""
        try:
            from rembg import new_session, remove

            session = ImagenClient._REMBG_SESSION
            if session is None:
                with ImagenClient._REMBG_INIT_LOCK:
                    session = ImagenClient._REMBG_SESSION
                    if session is None:
                        log.info("Initializing rembg session for sprite cutout")
                        session = new_session("u2net")
                        ImagenClient._REMBG_SESSION = session
            result = remove(img.convert("RGBA"), session=session)
            if isinstance(result, bytes):
                return Image.open(io.BytesIO(result)).convert("RGBA")
            if isinstance(result, Image.Image):
                return result.convert("RGBA")
        except Exception:
            log.debug("rembg background removal unavailable, using fallback", exc_info=True)
        return ImagenClient._remove_white_bg(img)

    @classmethod
    def _largest_alpha_component_bbox(cls, img: Image.Image) -> tuple[int, int, int, int] | None:
        """Keep the dominant opaque subject and ignore stray extra figures/fragments."""
        alpha = img.getchannel("A")
        width, height = img.size
        mask = alpha.load()
        visited = [[False] * height for _ in range(width)]
        best_bbox: tuple[int, int, int, int] | None = None
        best_area = 0

        for x in range(width):
            for y in range(height):
                if visited[x][y] or mask[x, y] <= cls._ALPHA_THRESHOLD:
                    continue
                queue: deque[tuple[int, int]] = deque([(x, y)])
                visited[x][y] = True
                min_x = max_x = x
                min_y = max_y = y
                count = 0
                while queue:
                    cx, cy = queue.popleft()
                    count += 1
                    min_x = min(min_x, cx)
                    max_x = max(max_x, cx)
                    min_y = min(min_y, cy)
                    max_y = max(max_y, cy)
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if not (0 <= nx < width and 0 <= ny < height):
                            continue
                        if visited[nx][ny] or mask[nx, ny] <= cls._ALPHA_THRESHOLD:
                            continue
                        visited[nx][ny] = True
                        queue.append((nx, ny))
                if count > best_area:
                    best_area = count
                    best_bbox = (min_x, min_y, max_x + 1, max_y + 1)
        return best_bbox

    @classmethod
    def _extract_primary_subject(cls, img: Image.Image) -> Image.Image:
        rgba = img.convert("RGBA")
        bbox = cls._largest_alpha_component_bbox(rgba)
        if not bbox:
            return rgba
        return rgba.crop(bbox)

    @classmethod
    def _normalize_sprite_canvas(cls, img: Image.Image) -> Image.Image:
        """Standardize sprite framing: one subject, centered, feet aligned, fixed canvas."""
        subject = cls._extract_primary_subject(img)
        canvas_w, canvas_h = cls._SPRITE_CANVAS
        max_w = int(canvas_w * (1 - cls._SPRITE_SIDE_MARGIN_RATIO * 2))
        max_h = canvas_h - cls._SPRITE_FOOT_MARGIN * 2
        subj_w, subj_h = subject.size
        if subj_w <= 0 or subj_h <= 0:
            return Image.new("RGBA", cls._SPRITE_CANVAS, (0, 0, 0, 0))
        scale = min(max_w / subj_w, max_h / subj_h)
        resized = subject.resize(
            (max(1, int(subj_w * scale)), max(1, int(subj_h * scale))),
            Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGBA", cls._SPRITE_CANVAS, (0, 0, 0, 0))
        pos_x = (canvas_w - resized.width) // 2
        pos_y = canvas_h - cls._SPRITE_FOOT_MARGIN - resized.height
        canvas.alpha_composite(resized, (pos_x, max(0, pos_y)))
        return canvas

    @classmethod
    def _prepare_sprite_asset(cls, img: Image.Image) -> Image.Image:
        cutout = cls._remove_background(img)
        normalized = cls._normalize_sprite_canvas(cutout)
        return normalized

    def generate_image(
        self,
        prompt: str,
        *,
        is_cg: bool = False,
        template: str | None = None,
        references: list[Path] | None = None,
    ) -> Path | None:
        """Generate an image and return its local path, or None on failure."""
        if template is None:
            template = CG_PROMPT_TEMPLATE if is_cg else VISUAL_PROMPT_TEMPLATE
        full_prompt = template.format(description=prompt)
        reference_key = "|".join(str(p) for p in references or [])
        model = self.promo_model if is_cg else self.model
        aspect_ratio = "3:4" if template is VISUAL_PROMPT_TEMPLATE else "16:9"

        cached = self._cache_path(model + "|" + full_prompt + reference_key)
        if cached.exists():
            log.debug("Cache hit: %s", cached)
            return cached

        try:
            img = self._request_image(
                model,
                full_prompt,
                references=references,
                aspect_ratio=aspect_ratio,
            )
            if img:
                # For character sprites (not CG/background): remove white background
                if template is VISUAL_PROMPT_TEMPLATE:
                    img = self._prepare_sprite_asset(img)
                    log.debug("Sprite cutout and normalization complete")
                img.save(cached, "PNG")
                log.info("Generated image saved: %s", cached)
                return cached
            log.warning("No image in response for prompt: %s", full_prompt[:80])
        except Exception:
            log.exception("Image generation failed for prompt: %s", full_prompt[:80])

        return None

    def generate_character_sprite(
        self,
        visual_description: str,
        *,
        references: list[Path] | None = None,
    ) -> Path | None:
        return self.generate_image(
            visual_description,
            is_cg=False,
            references=references,
        )

    def generate_background(
        self,
        description: str,
        *,
        references: list[Path] | None = None,
    ) -> Path | None:
        """Generate a background illustration."""
        return self.generate_image(
            description,
            template=BACKGROUND_PROMPT_TEMPLATE,
            references=references,
        )

    def generate_cg(
        self,
        cg_prompt: str,
        *,
        references: list[Path] | None = None,
    ) -> Path | None:
        return self.generate_image(
            cg_prompt,
            is_cg=True,
            references=references,
        )
