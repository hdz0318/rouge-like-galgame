"""Roguelike mechanics — random events, permadeath, meta-progression."""

from __future__ import annotations

import random


# Random disturbance events injected into scene generation
RANDOM_EVENTS = [
    "角色突然露出了与平时完全不同的表情，眼神变得阴暗。",
    "背景中传来了不属于这个场景的诡异音乐声。",
    "角色说出了一句不在剧本里的话，似乎在打破第四面墙。",
    "周围的环境开始扭曲，像是画面出了故障。",
    "角色短暂地消失了一瞬间，然后出现在了不同的位置。",
    "突然有另一个声音插入了对话，但看不到说话的人。",
    "角色的影子似乎在独立行动。",
    "时间似乎倒流了一小段，同样的对话重复了一遍但内容微妙不同。",
    "角色突然问了你一个私人问题，仿佛知道你是玩家。",
    "背景中出现了一个不应该存在的门。",
]


def roll_random_event(round_number: int, sanity: int) -> str:
    """Roll for a random disturbance event.

    Higher rounds and lower sanity increase event probability.
    """
    base_chance = 0.15
    sanity_bonus = (100 - sanity) / 200  # up to +0.5 at sanity=0
    round_bonus = min(round_number * 0.02, 0.2)  # up to +0.2

    if random.random() < base_chance + sanity_bonus + round_bonus:
        return random.choice(RANDOM_EVENTS)
    return ""


def generate_memory_fragment(history: list[str], round_number: int) -> str:
    """Generate a memory fragment for meta-progression on game over."""
    if not history:
        return f"第{round_number}轮：一段模糊的记忆，什么都想不起来了。"
    last = history[-1] if history else ""
    return f"第{round_number}轮的残影：{last[:50]}..."
