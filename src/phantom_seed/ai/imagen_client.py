"""OpenRouter image client for Gemini 3.1 Flash image generation."""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from openai import OpenAI
from PIL import Image

from phantom_seed.ai.prompts import BACKGROUND_PROMPT_TEMPLATE, CG_PROMPT_TEMPLATE, VISUAL_PROMPT_TEMPLATE

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)


class ImagenClient:
    """Image generation via OpenRouter using Gemini 3.1 Flash image model."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = OpenAI(
            base_url=config.openrouter_base_url,
            api_key=config.openrouter_api_key,
        )
        self.model = config.image_model
        self.cache_dir = config.cache_dir

    def _cache_path(self, prompt: str) -> Path:
        h = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        return self.cache_dir / f"{h}.png"

    def _request_image(self, full_prompt: str, aspect_ratio: str = "2:3") -> Image.Image | None:
        """Send one image generation request and return a PIL Image or None."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": full_prompt}],
            extra_headers={"HTTP-Referer": "https://phantom-seed.game"},
            extra_body={
                "modalities": ["image", "text"],
                "image_config": {"aspect_ratio": aspect_ratio},
            },
        )

        msg = response.choices[0].message
        raw = msg.model_extra or {}

        # OpenRouter returns images in message.images (not message.content)
        images_field = raw.get("images")
        if isinstance(images_field, list):
            for item in images_field:
                if isinstance(item, dict):
                    url = item.get("image_url", {}).get("url", "")
                    if url:
                        img = self._from_url_or_data_uri(url)
                        if img:
                            return img

        # Fallback: check structured content parts
        content_parts = None
        if isinstance(msg.content, list):
            content_parts = msg.content
        elif isinstance(raw.get("content"), list):
            content_parts = raw["content"]

        if content_parts:
            for part in content_parts:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    img = self._from_url_or_data_uri(url)
                    if img:
                        return img
                elif part.get("type") == "inline_data":
                    data = part.get("inline_data", {}).get("data", "")
                    if data:
                        img = self._decode_b64(data)
                        if img:
                            return img

        # Fallback: text-embedded base64 / URL
        text_content = msg.content if isinstance(msg.content, str) else ""
        if text_content:
            log.debug("Image response text (%d chars): %s", len(text_content), text_content[:200])
            img = self._extract_image(text_content)
            if img:
                return img

        log.warning("No image in response. raw keys: %s", list(raw.keys()))
        return None

    def generate_image(self, prompt: str, *, is_cg: bool = False, aspect_ratio: str = "2:3", template: str | None = None) -> Path | None:
        """Generate an image and return its local path, or None on failure."""
        if template is None:
            template = CG_PROMPT_TEMPLATE if is_cg else VISUAL_PROMPT_TEMPLATE
        full_prompt = template.format(description=prompt)

        cached = self._cache_path(full_prompt)
        if cached.exists():
            log.debug("Cache hit: %s", cached)
            return cached

        try:
            img = self._request_image(full_prompt, aspect_ratio=aspect_ratio)
            if img:
                img.save(cached, "PNG")
                log.info("Generated image saved: %s", cached)
                return cached
            log.warning("No image in response for prompt: %s", full_prompt[:80])
        except Exception:
            log.exception("Image generation failed for prompt: %s", full_prompt[:80])

        return None

    def _extract_image(self, content: str) -> Image.Image | None:
        """Try every known format to extract an image from text content."""
        # Markdown image: ![alt](url)
        m = re.search(r"!\[.*?\]\((https?://[^\s\)]+)\)", content)
        if m:
            return self._download(m.group(1))

        # Bare URL on its own line
        m = re.search(r"(https?://\S+\.(?:png|jpg|jpeg|webp)\S*)", content, re.IGNORECASE)
        if m:
            return self._download(m.group(1))

        # Any https URL (some providers return sandbox URLs without extension)
        m = re.search(r"(https?://\S+)", content)
        if m:
            img = self._download(m.group(1))
            if img:
                return img

        # data:image URI
        m = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+)", content)
        if m:
            return self._decode_b64(m.group(1))

        # Pure base64 blob
        stripped = content.strip()
        if len(stripped) > 200 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", stripped):
            return self._decode_b64(stripped)

        return None

    def _from_url_or_data_uri(self, url: str) -> Image.Image | None:
        if url.startswith("data:image"):
            m = re.search(r"base64,(.+)", url)
            if m:
                return self._decode_b64(m.group(1))
        if url.startswith("http"):
            return self._download(url)
        return None

    def _download(self, url: str) -> Image.Image | None:
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "image" in ct or resp.content[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"RIFF"):
                return Image.open(io.BytesIO(resp.content))
            log.debug("Downloaded URL was not an image (content-type: %s)", ct)
        except Exception:
            log.debug("Failed to download image from: %s", url[:120])
        return None

    def _decode_b64(self, data: str) -> Image.Image | None:
        try:
            raw = base64.b64decode(data.replace("\n", "").replace(" ", ""))
            return Image.open(io.BytesIO(raw))
        except Exception:
            log.debug("Failed to decode base64 image data")
            return None

    def generate_character_sprite(self, visual_description: str) -> Path | None:
        return self.generate_image(visual_description, is_cg=False, aspect_ratio="2:3")

    def generate_background(self, description: str) -> Path | None:
        """Generate a 16:9 background illustration."""
        return self.generate_image(description, aspect_ratio="16:9", template=BACKGROUND_PROMPT_TEMPLATE)

    def generate_cg(self, cg_prompt: str) -> Path | None:
        return self.generate_image(cg_prompt, is_cg=True, aspect_ratio="16:9")
