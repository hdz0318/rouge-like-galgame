"""SceneData generation chain."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Callable

from phantom_seed.ai.llm import OpenRouterClient
from phantom_seed.ai.prompts.scene import (
    build_scene_plan_messages,
    build_scene_review_messages,
    build_scene_write_messages,
)
from phantom_seed.ai.protocol import CharacterProfile, SceneData, ScenePlan

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)


class SceneChain:
    """Generates a SceneData segment with plan -> draft -> review steps."""

    def __init__(self, config: Config) -> None:
        self._client = OpenRouterClient(config.openrouter_api_key)
        self._planner_model = config.text_model
        self._writer_model = config.draft_text_model
        self._reviewer_model = config.text_model

    @staticmethod
    def _format_progress(stage: str, event: dict[str, object]) -> str:
        stage_label = {
            "plan": "剧情规划",
            "draft": "正文草拟",
            "review": "剧情审校",
        }.get(stage, stage)
        kind = str(event.get("type", ""))
        if kind == "final":
            usage = event.get("usage")
            if isinstance(usage, dict) and usage:
                prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
                completion_tokens = int(usage.get("completion_tokens", 0) or 0)
                total_tokens = int(usage.get("total_tokens", 0) or 0)
                return (
                    f"{stage_label} 完成 输{prompt_tokens}tok "
                    f"出{completion_tokens}tok 总{total_tokens}tok"
                )
            return f"{stage_label} 完成"
        return f"{stage_label} 模型处理中"

    def invoke(
        self,
        character_profile: CharacterProfile,
        cast_summary: str,
        active_heroine: str,
        affection: int,
        round_number: int,
        history_summary: str,
        story_memory: str,
        route_blueprint: str,
        ending_target: str,
        last_choice: str,
        random_event: str,
        chapter_beat: str = "",
        route_phase: str = "common",
        route_locked_to: str = "",
        progress_cb: Callable[[str], None] | None = None,
    ) -> SceneData:
        """Generate the next scene segment."""
        payload = {
            "character_profile": character_profile.model_dump_json(indent=2),
            "cast_summary": cast_summary,
            "active_heroine": active_heroine or character_profile.name,
            "affection": str(affection),
            "round_number": str(round_number),
            "chapter_beat": chapter_beat or "序章·邂逅",
            "route_phase": route_phase or "common",
            "route_locked_to": route_locked_to or "（未锁线）",
            "route_blueprint": route_blueprint or "暂无路线蓝图。",
            "ending_target": ending_target or "暂未决定结局等级。",
            "history_summary": history_summary or "这是故事的开始，一切从零开始。",
            "story_memory": story_memory or "暂无额外剧情记忆。",
            "last_choice": last_choice or "（无）",
            "random_event": random_event or "（无特殊事件）",
        }
        plan = self._client.structured_completion(
            model=self._planner_model,
            messages=build_scene_plan_messages(**payload),
            schema_model=ScenePlan,
            temperature=0.55,
            max_tokens=4096,
            stream_progress=(
                (lambda event: progress_cb(self._format_progress("plan", event)))
                if progress_cb
                else None
            ),
        )
        plan_json = plan.model_dump_json(indent=2)
        draft_payload = {**payload, "scene_plan": plan_json}
        draft = self._client.structured_completion(
            model=self._writer_model,
            messages=build_scene_write_messages(**draft_payload),
            schema_model=SceneData,
            temperature=0.9,
            max_tokens=8192,
            stream_progress=(
                (lambda event: progress_cb(self._format_progress("draft", event)))
                if progress_cb
                else None
            ),
        )
        review_payload = {
            **payload,
            "scene_plan": plan_json,
            "scene_draft": json.dumps(
                draft.model_dump(),
                ensure_ascii=False,
                indent=2,
            ),
        }
        result = self._client.structured_completion(
            model=self._reviewer_model,
            messages=build_scene_review_messages(**review_payload),
            schema_model=SceneData,
            temperature=0.45,
            max_tokens=8192,
            stream_progress=(
                (lambda event: progress_cb(self._format_progress("review", event)))
                if progress_cb
                else None
            ),
        )
        log.info(
            "Scene generated: %s | purpose=%s",
            result.scene_id,
            plan.scene_purpose,
        )
        return SceneData.model_validate(result)
