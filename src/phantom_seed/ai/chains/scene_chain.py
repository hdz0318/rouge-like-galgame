"""SceneData generation chain."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Callable

from phantom_seed.ai.llm import OpenRouterClient
from phantom_seed.ai.prompts.scene import (
    build_scene_critique_messages,
    build_scene_plan_messages,
    build_scene_review_messages,
    build_scene_write_messages,
)
from phantom_seed.ai.protocol import (
    AgentStageTrace,
    CharacterProfile,
    SceneCritique,
    SceneData,
    ScenePlan,
)

if TYPE_CHECKING:
    from phantom_seed.config import Config

log = logging.getLogger(__name__)


class SceneChain:
    """Generates a SceneData segment with an agentic plan -> draft -> critique -> review loop."""

    def __init__(self, config: Config, client: OpenRouterClient | None = None) -> None:
        self._client = client or OpenRouterClient(config.openrouter_api_key)
        self._planner_model = config.text_model
        self._writer_model = config.draft_text_model
        self._reviewer_model = config.text_model
        self._critic_model = config.text_model
        self._max_revision_rounds = max(1, config.scene_max_revision_rounds)
        self._quality_threshold = max(0, min(100, config.scene_quality_threshold))
        self._last_trace: list[AgentStageTrace] = []

    @property
    def last_trace(self) -> list[AgentStageTrace]:
        return list(self._last_trace)

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

    @staticmethod
    def _usage_from_event(event: dict[str, object]) -> tuple[int, int, int, str]:
        usage = event.get("usage")
        finish_reason = str(event.get("finish_reason", "") or "")
        if not isinstance(usage, dict):
            return 0, 0, 0, finish_reason
        return (
            int(usage.get("prompt_tokens", 0) or 0),
            int(usage.get("completion_tokens", 0) or 0),
            int(usage.get("total_tokens", 0) or 0),
            finish_reason,
        )

    def _run_structured_stage(
        self,
        *,
        stage_name: str,
        model: str,
        messages: list[dict[str, object]],
        schema_model,
        temperature: float,
        max_tokens: int,
        attempt: int,
        progress_cb: Callable[[str], None] | None,
    ):
        final_event: dict[str, object] = {}

        def stream_progress(event: dict[str, object]) -> None:
            nonlocal final_event
            if str(event.get("type", "")) == "final":
                final_event = dict(event)
            if progress_cb:
                progress_cb(self._format_progress(stage_name, event))

        result = self._client.structured_completion(
            model=model,
            messages=messages,
            schema_model=schema_model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream_progress=stream_progress if progress_cb else stream_progress,
        )
        prompt_tokens, completion_tokens, total_tokens, finish_reason = self._usage_from_event(
            final_event
        )
        self._last_trace.append(
            AgentStageTrace(
                stage=stage_name,
                model=model,
                status="ok",
                summary=f"{stage_name} attempt {attempt}",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
                attempt=attempt,
            )
        )
        return result

    def _passes_local_quality_gate(self, scene: SceneData) -> tuple[bool, list[str]]:
        issues: list[str] = []
        line_count = len(scene.script)
        if line_count < 20:
            issues.append(f"对话条数过少: {line_count}")
        transition_count = sum(1 for line in scene.script if line.scene_transition)
        if transition_count < 2:
            issues.append(f"场景切换次数不足: {transition_count}")
        if len(scene.choices) < 2:
            issues.append("选项数量不足")
        if not scene.scene_goal.strip():
            issues.append("scene_goal 为空")
        if not scene.next_hook.strip():
            issues.append("next_hook 为空")
        return not issues, issues

    @staticmethod
    def _revision_brief(critique: SceneCritique | None, local_issues: list[str]) -> str:
        notes: list[str] = []
        if critique:
            notes.extend(critique.blocking_issues)
            notes.extend(critique.improvement_notes[:3])
            notes.extend(critique.continuity_risks[:2])
        notes.extend(local_issues)
        cleaned = [note.strip() for note in notes if note and note.strip()]
        if not cleaned:
            return "无上一轮反馈，请直接按 scene_plan 产出高质量完整场景。"
        deduped: list[str] = []
        for note in cleaned:
            if note not in deduped:
                deduped.append(note)
        return "\n".join(f"- {note}" for note in deduped[:8])

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
        self._last_trace = []
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
        plan = self._run_structured_stage(
            stage_name="plan",
            model=self._planner_model,
            messages=build_scene_plan_messages(**payload),
            schema_model=ScenePlan,
            temperature=0.55,
            max_tokens=4096,
            attempt=1,
            progress_cb=progress_cb,
        )
        plan_json = plan.model_dump_json(indent=2)
        critique: SceneCritique | None = None
        local_issues: list[str] = []
        draft: SceneData | None = None
        for attempt in range(1, self._max_revision_rounds + 1):
            draft_payload = {
                **payload,
                "scene_plan": plan_json,
                "revision_brief": self._revision_brief(critique, local_issues),
            }
            draft = self._run_structured_stage(
                stage_name="draft",
                model=self._writer_model,
                messages=build_scene_write_messages(**draft_payload),
                schema_model=SceneData,
                temperature=0.9 if attempt == 1 else 0.72,
                max_tokens=8192,
                attempt=attempt,
                progress_cb=progress_cb,
            )
            critique_payload = {
                **payload,
                "scene_plan": plan_json,
                "scene_draft": json.dumps(
                    draft.model_dump(),
                    ensure_ascii=False,
                    indent=2,
                ),
            }
            critique = self._run_structured_stage(
                stage_name="critique",
                model=self._critic_model,
                messages=build_scene_critique_messages(**critique_payload),
                schema_model=SceneCritique,
                temperature=0.2,
                max_tokens=2048,
                attempt=attempt,
                progress_cb=progress_cb,
            )
            passes_local_gate, local_issues = self._passes_local_quality_gate(draft)
            should_retry = (
                critique.should_retry
                or not critique.passes
                or critique.overall_score < self._quality_threshold
                or not passes_local_gate
            )
            if not should_retry or attempt >= self._max_revision_rounds:
                break

        assert draft is not None
        review_payload = {
            **payload,
            "scene_plan": plan_json,
            "scene_draft": json.dumps(
                draft.model_dump(),
                ensure_ascii=False,
                indent=2,
            ),
        }
        result = self._run_structured_stage(
            stage_name="review",
            model=self._reviewer_model,
            messages=build_scene_review_messages(**review_payload),
            schema_model=SceneData,
            temperature=0.45,
            max_tokens=8192,
            attempt=1,
            progress_cb=progress_cb,
        )
        final_passes_local_gate, final_local_issues = self._passes_local_quality_gate(result)
        if not final_passes_local_gate:
            log.warning("Scene passed model review but failed local gate: %s", final_local_issues)
        log.info(
            "Scene generated: %s | purpose=%s | trace=%s",
            result.scene_id,
            plan.scene_purpose,
            [
                {
                    "stage": item.stage,
                    "attempt": item.attempt,
                    "tokens": item.total_tokens,
                }
                for item in self._last_trace
            ],
        )
        return SceneData.model_validate(result)
