"""Small file I/O helpers focused on safe local persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json_file(path: Path) -> Any:
    """Read and decode a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, data: Any) -> None:
    """Persist JSON atomically to avoid partially written save/settings files."""
    write_text_file(
        path,
        json.dumps(data, ensure_ascii=False, indent=2),
    )


def write_text_file(path: Path, content: str) -> None:
    """Write UTF-8 text atomically by replacing the destination in one step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="",
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)
    os.replace(temp_path, path)
