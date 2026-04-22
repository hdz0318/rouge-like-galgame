from __future__ import annotations

from pathlib import Path

from phantom_seed.utils.io import read_json_file, write_json_file, write_text_file


def test_write_text_file_replaces_contents_atomically(tmp_path: Path) -> None:
    path = tmp_path / "state.txt"
    write_text_file(path, "alpha")
    write_text_file(path, "beta")

    assert path.read_text(encoding="utf-8") == "beta"


def test_write_json_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    payload = {"text_speed_ms": 20, "fullscreen": False}

    write_json_file(path, payload)

    assert read_json_file(path) == payload
