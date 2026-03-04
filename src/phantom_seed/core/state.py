"""Game state management."""

from __future__ import annotations

from dataclasses import dataclass, field

# Chapter beats — drive narrative pacing
CHAPTER_BEATS = [
    "序章·相遇（铺垫人物关系，建立悬念）",
    "第一幕·异变（日常中出现第一个裂缝，引入核心矛盾）",
    "第二幕·试探（角色相互试探，隐藏信息逐渐露出冰山一角）",
    "第三幕·冲突（正面矛盾爆发，揭示一个重大秘密）",
    "第四幕·深渊（主角心理开始动摇，理智值危机或感情危机）",
    "第五幕·真相碎片（核心秘密几乎被揭穿，角色做出关键选择）",
    "终章·收束（路线分叉，走向不同结局）",
]


@dataclass
class GameState:
    """Tracks all mutable game state for the current run."""

    sanity: int = 100
    favor: int = 0
    round_number: int = 0
    history: list[str] = field(default_factory=list)
    memory_fragments: list[str] = field(default_factory=list)  # meta-progression
    is_game_over: bool = False
    is_ending: bool = False

    @property
    def chapter_beat(self) -> str:
        idx = min(self.round_number, len(CHAPTER_BEATS) - 1)
        return CHAPTER_BEATS[idx]

    def apply_delta(self, delta: dict[str, int]) -> None:
        """Apply stat changes from a choice."""
        self.sanity = max(0, min(100, self.sanity + delta.get("sanity", 0)))
        self.favor = max(0, min(100, self.favor + delta.get("favor", 0)))
        if self.sanity <= 0:
            self.is_game_over = True

    def advance_round(self) -> None:
        self.round_number += 1

    def add_history(self, summary: str) -> None:
        self.history.append(summary)
        # Keep history compact — only last 15 entries
        if len(self.history) > 15:
            self.history = self.history[-15:]

    def get_history_summary(self) -> str:
        if not self.history:
            return "这是故事的开始，一切从零开始。"
        return "\n".join(f"- {h}" for h in self.history)

    def reset_for_new_run(self) -> None:
        """Reset for a new roguelike run, keeping meta-progression."""
        fragments = self.memory_fragments.copy()
        self.sanity = 100
        self.favor = 0
        self.round_number = 0
        self.history.clear()
        self.is_game_over = False
        self.is_ending = False
        self.memory_fragments = fragments
