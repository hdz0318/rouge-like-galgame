"""Game state management."""

from __future__ import annotations

from dataclasses import dataclass, field

from phantom_seed.ai.protocol import SceneData

# Chapter beats — romance narrative arc
CHAPTER_BEATS = [
    "序章·邂逅（命运般的相遇，建立第一印象）",
    "第一幕·接近（日常互动增多，逐渐熟悉彼此）",
    "第二幕·心动（不经意间的心跳加速，暧昧的气氛）",
    "第三幕·波澜（误会或小冲突，考验两人的关系）",
    "第四幕·坦诚（敞开心扉，分享内心深处的想法）",
    "第五幕·告白（鼓起勇气表达心意，命运的抉择）",
    "终章·结局（故事走向各自的结局）",
]

ROUTE_PHASE_LABELS = {
    "common": "共通线前半",
    "lock_window": "共通线分歧窗口",
    "heroine_route": "个人线推进",
    "climax": "个人线高潮",
    "ending": "结局幕",
}


@dataclass
class GameState:
    """Tracks all mutable game state for the current run."""

    affection: int = 0
    heroine_affection: dict[str, int] = field(default_factory=dict)
    active_heroine: str = ""
    route_phase: str = "common"
    route_locked_to: str = ""
    round_number: int = 0
    history: list[str] = field(default_factory=list)
    memory_fragments: list[str] = field(default_factory=list)  # meta-progression
    continuity_notes: list[str] = field(default_factory=list)
    open_threads: list[str] = field(default_factory=list)
    recent_locations: list[str] = field(default_factory=list)
    latest_hook: str = ""
    is_ending: bool = False

    @property
    def chapter_beat(self) -> str:
        idx = min(self.round_number, len(CHAPTER_BEATS) - 1)
        return CHAPTER_BEATS[idx]

    @property
    def relationship_stage(self) -> str:
        if self.affection < 30:
            return "初识试探"
        if self.affection < 60:
            return "逐渐亲近"
        if self.affection < 80:
            return "暧昧升温"
        return "深度依恋"

    @property
    def route_phase_label(self) -> str:
        return ROUTE_PHASE_LABELS.get(self.route_phase, self.route_phase)

    def register_heroine(self, name: str, *, initial_affection: int = 0) -> None:
        if name not in self.heroine_affection:
            self.heroine_affection[name] = max(0, min(100, initial_affection))
        if not self.active_heroine:
            self.set_active_heroine(name)

    def set_active_heroine(self, name: str) -> None:
        if not name:
            return
        self.active_heroine = name
        self.affection = self.heroine_affection.get(name, self.affection)

    def heroine_score(self, name: str) -> int:
        return self.heroine_affection.get(name, 0)

    def ranked_heroines(self) -> list[tuple[str, int]]:
        return sorted(
            self.heroine_affection.items(),
            key=lambda item: (-item[1], item[0]),
        )

    def update_route_state(self) -> None:
        if self.route_locked_to:
            if self.round_number >= 9:
                self.route_phase = "ending"
            elif self.round_number >= 8:
                self.route_phase = "climax"
            else:
                self.route_phase = "heroine_route"
            self.set_active_heroine(self.route_locked_to)
            return
        ranked = self.ranked_heroines()
        if not ranked:
            self.route_phase = "common"
            return
        lead_name, lead_score = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        if self.round_number >= 5 and lead_score >= 55 and lead_score - runner_up >= 10:
            self.route_locked_to = lead_name
            self.route_phase = "heroine_route"
            self.set_active_heroine(lead_name)
            return
        if self.round_number >= 7:
            self.route_locked_to = lead_name
            self.route_phase = "heroine_route"
            self.set_active_heroine(lead_name)
            return
        if self.round_number >= 5:
            self.route_phase = "lock_window"
        else:
            self.route_phase = "common"
        if not self.active_heroine:
            self.set_active_heroine(lead_name)

    def route_blueprint(self) -> str:
        active = self.route_locked_to or self.active_heroine or "待定"
        lines = [
            f"- 当前线路阶段：{self.route_phase_label}",
            "- 商业 galgame 参考流程：",
            "  - 第1-4幕：共通线，平衡塑造多名女主魅力与伏笔。",
            "  - 第5-7幕：进入锁线窗口，玩家选择应明显偏向某位女主。",
            "  - 第8幕：锁线后的高潮幕，集中爆发个人矛盾与情感表白。",
            "  - 第9幕及以后：对应线路结局幕，根据女主好感与回收情况决定结局质量。",
            f"- 当前预期主线路女主：{active}",
        ]
        if self.route_locked_to:
            score = self.heroine_score(self.route_locked_to)
            lines.append(
                f"- {self.route_locked_to} 当前线路分数：{score}，目标是让高潮与结局围绕她展开。"
            )
        return "\n".join(lines)

    def ending_grade(self, heroine_name: str) -> str:
        score = self.heroine_score(heroine_name)
        if score >= 85:
            return "true"
        if score >= 72:
            return "good"
        if score >= 60:
            return "normal"
        return "bittersweet"

    def apply_delta(self, delta: dict[str, int]) -> None:
        """Apply stat changes from a choice."""
        active_name = self.route_locked_to or self.active_heroine
        if "affection" in delta:
            new_score = max(0, min(100, self.affection + delta["affection"]))
            self.affection = new_score
            if active_name:
                self.heroine_affection[active_name] = new_score
        for key, value in delta.items():
            if not key.startswith("heroine:"):
                continue
            heroine_name = key.split(":", 1)[1].strip()
            if not heroine_name:
                continue
            current = self.heroine_affection.get(heroine_name, 0)
            self.heroine_affection[heroine_name] = max(0, min(100, current + value))
        if active_name:
            self.affection = self.heroine_affection.get(active_name, self.affection)
        self.update_route_state()

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

    def get_story_memory(self) -> str:
        parts = [
            f"- 关系阶段：{self.relationship_stage}",
            f"- 当前章节：{self.chapter_beat}",
            f"- 路线阶段：{self.route_phase_label}",
        ]
        if self.active_heroine:
            parts.append(f"- 当前焦点女主：{self.active_heroine}")
        if self.route_locked_to:
            parts.append(f"- 已锁定个人线：{self.route_locked_to}")
        if self.heroine_affection:
            parts.append("- 女主好感排行：")
            parts.extend(
                f"  - {name}: {score}"
                for name, score in self.ranked_heroines()[:4]
            )
        if self.continuity_notes:
            parts.append("- 必须延续的既有事实：")
            parts.extend(f"  - {note}" for note in self.continuity_notes[-5:])
        if self.open_threads:
            parts.append("- 尚未回收的伏笔/问题：")
            parts.extend(f"  - {thread}" for thread in self.open_threads[-4:])
        if self.recent_locations:
            parts.append(
                "- 最近去过的地点："
                + " / ".join(self.recent_locations[-4:])
            )
        if self.memory_fragments:
            parts.append(
                "- 长期记忆碎片："
                + " / ".join(self.memory_fragments[-3:])
            )
        if self.latest_hook:
            parts.append(f"- 上一幕留下的钩子：{self.latest_hook}")
        return "\n".join(parts)

    def remember_scene(self, scene: SceneData) -> None:
        if scene.continuity_notes:
            self.continuity_notes.extend(scene.continuity_notes)
            self.continuity_notes = self.continuity_notes[-10:]
        if scene.open_threads:
            merged = self.open_threads + scene.open_threads
            deduped: list[str] = []
            for item in merged:
                cleaned = item.strip()
                if cleaned and cleaned not in deduped:
                    deduped.append(cleaned)
            self.open_threads = deduped[-6:]
        if scene.background:
            self.recent_locations.append(scene.background[:80])
        for line in scene.script:
            if line.scene_transition:
                self.recent_locations.append(line.scene_transition[:80])
        self.recent_locations = self.recent_locations[-6:]
        self.latest_hook = scene.next_hook.strip()
        if scene.game_state_update.is_ending:
            self.open_threads.clear()

    def reset_for_new_run(self) -> None:
        """Reset for a new run, keeping meta-progression."""
        fragments = self.memory_fragments.copy()
        self.affection = 0
        self.heroine_affection.clear()
        self.active_heroine = ""
        self.route_phase = "common"
        self.route_locked_to = ""
        self.round_number = 0
        self.history.clear()
        self.continuity_notes.clear()
        self.open_threads.clear()
        self.recent_locations.clear()
        self.latest_hook = ""
        self.is_ending = False
        self.memory_fragments = fragments
