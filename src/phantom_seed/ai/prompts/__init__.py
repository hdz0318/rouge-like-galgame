"""Prompt helpers for AI generation."""

from phantom_seed.ai.prompts.character import build_character_messages
from phantom_seed.ai.prompts.scene import (
    build_scene_plan_messages,
    build_scene_review_messages,
    build_scene_write_messages,
)
from phantom_seed.ai.prompts.system import CHARACTER_SYSTEM_MESSAGE, SYSTEM_MESSAGE
from phantom_seed.ai.prompts.visual import (
    BACKGROUND_PROMPT_TEMPLATE,
    CG_PROMPT_TEMPLATE,
    VISUAL_PROMPT_TEMPLATE,
)

__all__ = [
    "BACKGROUND_PROMPT_TEMPLATE",
    "CG_PROMPT_TEMPLATE",
    "CHARACTER_SYSTEM_MESSAGE",
    "SYSTEM_MESSAGE",
    "VISUAL_PROMPT_TEMPLATE",
    "build_character_messages",
    "build_scene_plan_messages",
    "build_scene_review_messages",
    "build_scene_write_messages",
]
