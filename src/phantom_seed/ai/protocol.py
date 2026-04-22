"""JSON Script Protocol — Pydantic models for AI-generated scene data."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class VisualType(str, Enum):
    SPRITE_SCENE = "SPRITE_SCENE"
    CINEMATIC_CG = "CINEMATIC_CG"


class StageAction(str, Enum):
    ENTER = "enter"
    LEAVE = "leave"
    MOVE = "move"


class Position(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class StageCommand(BaseModel):
    action: StageAction
    character: str
    pos: Position = Position.CENTER
    expression: str = "default"


class DialogueLine(BaseModel):
    speaker: str
    text: str = ""
    inner_monologue: str = ""
    scene_transition: str = ""  # if set, switch background before rendering this line

    @model_validator(mode="before")
    @classmethod
    def _coerce_missing_text(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "text" not in data or data.get("text") is None:
            fallback = data.get("inner_monologue") or data.get("scene_transition") or ""
            data = {**data, "text": fallback}
        return data


class Choice(BaseModel):
    text: str
    target_state_delta: dict[str, int] = Field(default_factory=dict)


class GameStateUpdate(BaseModel):
    is_climax: bool = False
    is_ending: bool = False


class ScenePlan(BaseModel):
    """High-level narrative plan used before drafting a scene."""

    scene_purpose: str = ""
    opening_situation: str = ""
    emotional_beats: list[str] = Field(default_factory=list)
    continuity_must_use: list[str] = Field(default_factory=list)
    location_sequence: list[str] = Field(default_factory=list)
    conflict_turn: str = ""
    payoff_target: str = ""
    ending_hook: str = ""
    choice_design: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_alternate_plan_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if isinstance(normalized.get("scene_purpose"), dict):
            scene_purpose = normalized["scene_purpose"]
            normalized["scene_purpose"] = " | ".join(
                str(scene_purpose.get(key, "")).strip()
                for key in ("goal", "summary", "purpose")
                if str(scene_purpose.get(key, "")).strip()
            )
        if not normalized.get("scene_purpose"):
            alt = normalized.get("scene_goal") or normalized.get("goal")
            if alt:
                normalized["scene_purpose"] = alt
        if not normalized.get("opening_situation"):
            alt_opening = (
                normalized.get("opening")
                or normalized.get("opening_state")
                or normalized.get("scene_opening")
                or normalized.get("initial_situation")
                or normalized.get("setup")
                or normalized.get("scene_setup")
            )
            if alt_opening:
                normalized["opening_situation"] = alt_opening
        elif isinstance(normalized.get("opening_situation"), dict):
            opening = normalized["opening_situation"]
            summary_parts = [
                str(opening.get(key, "")).strip()
                for key in ("location", "situation", "summary", "goal")
                if str(opening.get(key, "")).strip()
            ]
            if summary_parts:
                normalized["opening_situation"] = " | ".join(summary_parts)
        raw_locations = normalized.get("location_sequence")
        if isinstance(raw_locations, list):
            rewritten_locations: list[str] = []
            for item in raw_locations:
                if isinstance(item, str):
                    rewritten_locations.append(item)
                    continue
                if isinstance(item, dict):
                    summary_parts = [
                        str(item.get(key, "")).strip()
                        for key in ("location", "purpose", "summary", "event")
                        if str(item.get(key, "")).strip()
                    ]
                    rewritten_locations.append(
                        " | ".join(summary_parts) if summary_parts else str(item)
                    )
                    continue
                rewritten_locations.append(str(item))
            normalized["location_sequence"] = rewritten_locations
        if not normalized.get("opening_situation"):
            raw_locations = normalized.get("location_sequence")
            if isinstance(raw_locations, list):
                for item in raw_locations:
                    text = str(item).strip()
                    if text:
                        normalized["opening_situation"] = text
                        break
        if not normalized.get("scene_purpose"):
            for key in ("payoff_target", "conflict_turn", "ending_hook"):
                text = str(normalized.get(key, "")).strip()
                if text:
                    normalized["scene_purpose"] = text
                    break
        raw_choice_design = normalized.get("choice_design")
        if isinstance(raw_choice_design, list):
            rewritten: list[str] = []
            for item in raw_choice_design:
                if isinstance(item, str):
                    rewritten.append(item)
                    continue
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    extras = [
                        f"{key}={value}"
                        for key, value in item.items()
                        if key != "text"
                    ]
                    summary = text or "选项方向"
                    if extras:
                        summary = f"{summary} | {'; '.join(extras)}"
                    rewritten.append(summary)
                    continue
                rewritten.append(str(item))
            normalized["choice_design"] = rewritten
        return normalized


class SceneScriptDraft(BaseModel):
    """Script-first scene draft before metadata/choices are filled in."""

    scene_id: str
    script: list[DialogueLine] = Field(default_factory=list)
    stage_commands: list[StageCommand] = Field(default_factory=list)
    scene_goal: str = ""


class SceneMetadataDraft(BaseModel):
    """Metadata and branching data generated after the script draft is available."""

    background: str = ""
    visual_type: VisualType = VisualType.SPRITE_SCENE
    climax_cg_prompt: str = ""
    choices: list[Choice] = Field(default_factory=list)
    game_state_update: GameStateUpdate = Field(default_factory=GameStateUpdate)
    emotional_shift: str = ""
    continuity_notes: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    next_hook: str = ""


class SceneCritique(BaseModel):
    """Quality assessment for a generated scene draft."""

    passes: bool = True
    overall_score: int = 80
    blocking_issues: list[str] = Field(default_factory=list)
    improvement_notes: list[str] = Field(default_factory=list)
    continuity_risks: list[str] = Field(default_factory=list)
    choice_quality: str = ""
    pacing_quality: str = ""
    should_retry: bool = False


class AgentStageTrace(BaseModel):
    """Observability record for one agent stage."""

    stage: str
    model: str
    status: str = "ok"
    summary: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    attempt: int = 1


class SceneData(BaseModel):
    """A single scene segment returned by the AI."""

    scene_id: str
    background: str = ""
    visual_type: VisualType = VisualType.SPRITE_SCENE
    stage_commands: list[StageCommand] = Field(default_factory=list)
    script: list[DialogueLine] = Field(default_factory=list)
    climax_cg_prompt: str = ""
    choices: list[Choice] = Field(default_factory=list)
    game_state_update: GameStateUpdate = Field(default_factory=GameStateUpdate)
    scene_goal: str = ""
    emotional_shift: str = ""
    continuity_notes: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    next_hook: str = ""


class CharacterProfile(BaseModel):
    """Character soul profile generated from a seed."""

    name: str
    personality: str
    speech_pattern: str
    visual_description: str
    signature_look: str = ""
    backstory: str = ""
    secrets: list[str] = Field(default_factory=list)
    relationship_to_player: str = ""


# Fallback template for when AI generation fails
FALLBACK_SCENE = SceneData(
    scene_id="fallback_001",
    background="sunny classroom with warm light streaming through windows",
    visual_type=VisualType.SPRITE_SCENE,
    script=[
        DialogueLine(
            speaker="???",
            text="你在看什么呢？",
            inner_monologue="阳光从窗外洒进来，空气中飘着淡淡的花香。",
        ),
        DialogueLine(
            speaker="???",
            text="嘛，没关系。稍等一下哦。",
        ),
    ],
    choices=[
        Choice(text="搭话试试", target_state_delta={"affection": 2}),
        Choice(text="安静地等待", target_state_delta={}),
    ],
)
