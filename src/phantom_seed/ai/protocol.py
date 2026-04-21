"""JSON Script Protocol — Pydantic models for AI-generated scene data."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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
    text: str
    inner_monologue: str = ""
    scene_transition: str = ""  # if set, switch background before rendering this line


class Choice(BaseModel):
    text: str
    target_state_delta: dict[str, int] = Field(default_factory=dict)


class GameStateUpdate(BaseModel):
    is_climax: bool = False
    is_ending: bool = False


class ScenePlan(BaseModel):
    """High-level narrative plan used before drafting a scene."""

    scene_purpose: str
    opening_situation: str
    emotional_beats: list[str] = Field(default_factory=list)
    continuity_must_use: list[str] = Field(default_factory=list)
    location_sequence: list[str] = Field(default_factory=list)
    conflict_turn: str = ""
    payoff_target: str = ""
    ending_hook: str = ""
    choice_design: list[str] = Field(default_factory=list)


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
