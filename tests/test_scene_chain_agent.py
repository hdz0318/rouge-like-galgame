from __future__ import annotations

from typing import Any

from phantom_seed.ai.chains.scene_chain import SceneChain
from phantom_seed.ai.protocol import CharacterProfile, SceneCritique, SceneData, ScenePlan
from phantom_seed.config import Config


class _FakeClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def structured_completion(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        response = self.responses[len(self.calls) - 1]
        if kwargs.get("stream_progress"):
            kwargs["stream_progress"](
                {
                    "type": "final",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                    },
                    "finish_reason": "stop",
                }
            )
        return response


def _make_scene(*, scene_id: str, lines: int, transitions: int) -> SceneData:
    script = []
    for idx in range(lines):
        script.append(
            {
                "speaker": "朝雾 澪" if idx % 2 == 0 else "主角",
                "text": f"line-{idx}",
                "scene_transition": f"anime campus bg {idx}"
                if idx < transitions
                else "",
            }
        )
    return SceneData.model_validate(
        {
            "scene_id": scene_id,
            "background": "anime classroom background",
            "script": script,
            "choices": [
                {"text": "靠近她", "target_state_delta": {"affection": 3}},
                {"text": "转移话题", "target_state_delta": {"affection": 0}},
            ],
            "scene_goal": "推进关系",
            "emotional_shift": "从试探到靠近",
            "continuity_notes": ["她提到过去的约定"],
            "open_threads": ["约定的真相尚未说明"],
            "next_hook": "夜晚的再会",
        }
    )


def test_scene_chain_retries_when_critique_requests_regeneration() -> None:
    config = Config()
    client = _FakeClient(
        [
            ScenePlan.model_validate(
                {
                    "scene_purpose": "推进关系",
                    "opening_situation": "放学后偶遇",
                    "emotional_beats": ["试探", "靠近"],
                }
            ),
            _make_scene(scene_id="draft-1", lines=10, transitions=1),
            SceneCritique.model_validate(
                {
                    "passes": False,
                    "overall_score": 60,
                    "blocking_issues": ["对话不足", "转场不足"],
                    "should_retry": True,
                }
            ),
            _make_scene(scene_id="draft-2", lines=26, transitions=2),
            SceneCritique.model_validate(
                {
                    "passes": True,
                    "overall_score": 88,
                    "improvement_notes": ["结尾钩子清晰"],
                    "should_retry": False,
                }
            ),
            _make_scene(scene_id="final", lines=28, transitions=2),
        ]
    )
    chain = SceneChain(config, client=client)  # type: ignore[arg-type]

    result = chain.invoke(
        character_profile=CharacterProfile.model_validate(
            {
                "name": "朝雾 澪",
                "personality": "冷静温柔",
                "speech_pattern": "简洁真诚",
                "visual_description": "anime heroine",
            }
        ),
        cast_summary="- 朝雾 澪",
        active_heroine="朝雾 澪",
        affection=20,
        round_number=2,
        history_summary="故事刚开始。",
        story_memory="暂无",
        route_blueprint="共通线推进",
        ending_target="good ending",
        last_choice="靠近她",
        random_event="下雨",
    )

    assert result.scene_id == "final"
    assert [item.stage for item in chain.last_trace] == [
        "plan",
        "draft",
        "critique",
        "draft",
        "critique",
        "review",
    ]


def test_scene_chain_records_trace_for_each_stage() -> None:
    config = Config()
    client = _FakeClient(
        [
            ScenePlan.model_validate(
                {
                    "scene_purpose": "推进关系",
                    "opening_situation": "咖啡馆谈心",
                }
            ),
            _make_scene(scene_id="draft-ok", lines=24, transitions=2),
            SceneCritique.model_validate(
                {
                    "passes": True,
                    "overall_score": 90,
                    "should_retry": False,
                }
            ),
            _make_scene(scene_id="final-ok", lines=25, transitions=2),
        ]
    )
    chain = SceneChain(config, client=client)  # type: ignore[arg-type]

    chain.invoke(
        character_profile=CharacterProfile.model_validate(
            {
                "name": "朝雾 澪",
                "personality": "冷静温柔",
                "speech_pattern": "简洁真诚",
                "visual_description": "anime heroine",
            }
        ),
        cast_summary="- 朝雾 澪",
        active_heroine="朝雾 澪",
        affection=20,
        round_number=2,
        history_summary="故事刚开始。",
        story_memory="暂无",
        route_blueprint="共通线推进",
        ending_target="good ending",
        last_choice="靠近她",
        random_event="下雨",
    )

    assert len(chain.last_trace) == 4
    assert all(item.total_tokens == 30 for item in chain.last_trace)
