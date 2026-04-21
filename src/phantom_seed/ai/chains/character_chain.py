"""CharacterProfile generation chain."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from phantom_seed.ai.llm import OpenRouterClient
from phantom_seed.ai.prompts.character import build_character_messages
from phantom_seed.ai.protocol import CharacterProfile

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)


class CharacterChain:
    """Generates a CharacterProfile via OpenRouter structured outputs."""

    def __init__(self, config: Config) -> None:
        self._client = OpenRouterClient(config.openrouter_api_key)
        self._model = config.text_model
        self._temperature = 0.65
        self._max_tokens = 1400

    @staticmethod
    def _format_progress(event: dict[str, object]) -> str:
        kind = str(event.get("type", ""))
        if kind == "final":
            usage = event.get("usage")
            if isinstance(usage, dict) and usage:
                prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                completion_tokens = int(usage.get("completion_tokens", 0) or 0)
                total_tokens = int(usage.get("total_tokens", 0) or 0)
                return (
                    f"人设完成 输{prompt_tokens}tok 出{completion_tokens}tok "
                    f"总{total_tokens}tok"
                )
            return "人设完成"
        return "人设生成中"

    def invoke(
        self,
        seed_hash: str,
        trait_code: str,
        progress_cb: Callable[[str], None] | None = None,
    ) -> CharacterProfile:
        """Generate a character profile from seed parameters."""
        result = self._client.structured_completion(
            model=self._model,
            messages=build_character_messages(seed_hash, trait_code),
            schema_model=CharacterProfile,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream_progress=(
                (lambda event: progress_cb(self._format_progress(event)))
                if progress_cb
                else None
            ),
        )
        log.info("Character generated: %s", result.name)
        return CharacterProfile.model_validate(result)
