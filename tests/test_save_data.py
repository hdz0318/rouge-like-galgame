from __future__ import annotations

import json

from phantom_seed.core.save_system import SaveData


def test_save_data_from_json_backfills_legacy_fields() -> None:
    raw = {
        "version": "1.0",
        "slot": "1",
        "timestamp": "2026-04-22 12:00",
        "seed_hash": "abc",
        "atmosphere": "rainy",
        "round_number": 2,
        "history": [],
        "memory_fragments": [],
        "is_ending": False,
        "character_data": {},
        "character_sprite_path": None,
        "current_scene_data": None,
        "dialogue_index": 0,
        "backlog": [],
    }

    data = SaveData.from_json(json.dumps(raw, ensure_ascii=False))

    assert data.affection == 0
    assert data.heroine_affection == {}
    assert data.route_phase == "common"
    assert data.heroines_data == []
    assert data.heroine_sprite_paths == {}

