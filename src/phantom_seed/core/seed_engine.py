"""Seed DNA engine — converts a player seed into initial game parameters."""

from __future__ import annotations

import hashlib


def hash_seed(seed_string: str) -> str:
    """Convert a player-entered string into a deterministic hex hash."""
    return hashlib.sha256(seed_string.encode("utf-8")).hexdigest()


def derive_trait_code(seed_hash: str) -> str:
    """Extract a 4-character trait code from the seed hash.

    This code is used to hint personality archetype to the AI.
    """
    # Use different segments of the hash for variety
    segment = int(seed_hash[:8], 16)
    archetypes = [
        "COOL",  # 冷酷系
        "YANDERE",  # 病娇系
        "GENKI",  # 元气系
        "KUUDERE",  # 酷系
        "MYSTERIOUS",  # 神秘系
        "GENTLE",  # 温柔系
        "TSUNDERE",  # 傲娇系
        "BROKEN",  # 崩坏系
    ]
    return archetypes[segment % len(archetypes)]


def derive_initial_atmosphere(seed_hash: str) -> str:
    """Derive the starting atmosphere/setting from the seed."""
    segment = int(seed_hash[8:16], 16)
    settings = [
        "abandoned_school",
        "moonlit_mansion",
        "endless_library",
        "underwater_city",
        "floating_garden",
        "clockwork_tower",
        "mirror_labyrinth",
        "twilight_train",
    ]
    return settings[segment % len(settings)]
