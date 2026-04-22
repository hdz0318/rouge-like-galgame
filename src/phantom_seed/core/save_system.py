"""Save / Load system for Phantom Seed.

Each save slot is a single JSON file stored in  <project_root>/.saves/
containing the *complete* reconstructible game state:
  - GameState (affection, round, history, memory_fragments)
  - CharacterProfile
  - All local asset paths (sprite + bg_cache)
  - Current SceneData + dialogue index
  - Full dialogue backlog
  - Small base64 thumbnail screenshot
"""

from __future__ import annotations

import base64
import io
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from phantom_seed.utils.io import read_json_file, write_text_file

if TYPE_CHECKING:
    import pygame

    from phantom_seed.core.coordinator import GameCoordinator

log = logging.getLogger(__name__)

SAVE_VERSION = "3.0"
SLOT_NAMES = ["QUICK", "1", "2", "3"]


@dataclass
class BacklogEntry:
    speaker: str
    text: str
    inner_monologue: str = ""
    scene_id: str = ""


@dataclass
class SaveData:
    version: str
    slot: str
    timestamp: str
    seed_hash: str
    atmosphere: str
    # GameState
    affection: int
    heroine_affection: dict[str, int]
    active_heroine: str
    route_phase: str
    route_locked_to: str
    round_number: int
    history: list[str]
    memory_fragments: list[str]
    continuity_notes: list[str]
    open_threads: list[str]
    recent_locations: list[str]
    latest_hook: str
    is_ending: bool
    # Character
    character_data: dict[str, Any]
    character_sprite_path: str | None
    heroines_data: list[dict[str, Any]]
    heroine_sprite_paths: dict[str, str]
    # Assets
    bg_cache: dict[str, str]
    # Scene
    current_scene_data: dict[str, Any] | None
    dialogue_index: int
    # Backlog of every line seen
    backlog: list[dict[str, str]]
    # Thumbnail (base64 PNG ~160×90)
    thumbnail_b64: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(text: str) -> SaveData:
        d = json.loads(text)
        # Migration from v1.0: drop removed fields
        d.pop("sanity", None)
        d.pop("favor", None)
        d.pop("is_game_over", None)
        if "affection" not in d:
            d["affection"] = 0
        d.setdefault("heroine_affection", {})
        d.setdefault("active_heroine", "")
        d.setdefault("route_phase", "common")
        d.setdefault("route_locked_to", "")
        d.setdefault("continuity_notes", [])
        d.setdefault("open_threads", [])
        d.setdefault("recent_locations", [])
        d.setdefault("latest_hook", "")
        d.setdefault("heroines_data", [])
        d.setdefault("heroine_sprite_paths", {})
        d.setdefault("bg_cache", {})
        return SaveData(**d)


class SaveSystem:
    """Manages serialisation and persistence of save slots."""

    def __init__(self, project_root: Path) -> None:
        self.save_dir = project_root / ".saves"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._slot_info_cache: dict[str, tuple[int, dict[str, str]]] = {}

    def _slot_path(self, slot: str) -> Path:
        return self.save_dir / f"slot_{slot}.json"

    def _invalidate_slot_info(self, slot: str) -> None:
        self._slot_info_cache.pop(slot, None)

    # ── Save ────────────────────────────────────────────────────

    def save(
        self,
        slot: str,
        coordinator: GameCoordinator,
        dialogue_index: int,
        backlog: list[BacklogEntry],
        screenshot: pygame.Surface | None = None,
    ) -> None:
        """Serialise the full game state to a slot file."""
        st = coordinator.state
        char = coordinator.character

        thumbnail_b64: str | None = None
        if screenshot is not None:
            try:
                import pygame

                small = pygame.transform.smoothscale(screenshot, (240, 135))
                buf = io.BytesIO()
                pygame.image.save(small, buf, "PNG")
                thumbnail_b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                log.debug("Thumbnail capture failed", exc_info=True)

        current_scene = coordinator.current_scene
        save = SaveData(
            version=SAVE_VERSION,
            slot=slot,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            seed_hash=coordinator.seed_hash,
            atmosphere=coordinator.atmosphere,
            affection=st.affection,
            heroine_affection=dict(st.heroine_affection),
            active_heroine=st.active_heroine,
            route_phase=st.route_phase,
            route_locked_to=st.route_locked_to,
            round_number=st.round_number,
            history=list(st.history),
            memory_fragments=list(st.memory_fragments),
            continuity_notes=list(st.continuity_notes),
            open_threads=list(st.open_threads),
            recent_locations=list(st.recent_locations),
            latest_hook=st.latest_hook,
            is_ending=st.is_ending,
            character_data=char.model_dump() if char else {},
            character_sprite_path=(
                str(coordinator.character_sprite_path)
                if coordinator.character_sprite_path
                else None
            ),
            heroines_data=[heroine.model_dump() for heroine in coordinator.heroines],
            heroine_sprite_paths={
                name: str(path) for name, path in coordinator.heroine_sprite_paths.items()
            },
            bg_cache=dict(coordinator._bg_cache),
            current_scene_data=current_scene.model_dump() if current_scene else None,
            dialogue_index=dialogue_index,
            backlog=[asdict(e) for e in backlog],
            thumbnail_b64=thumbnail_b64,
        )

        path = self._slot_path(slot)
        write_text_file(path, save.to_json())
        self._invalidate_slot_info(slot)
        log.info("Saved to slot %s: %s", slot, path)

    # ── Load ────────────────────────────────────────────────────

    def load(self, slot: str) -> SaveData | None:
        """Deserialise a save slot. Returns None if not found."""
        path = self._slot_path(slot)
        if not path.exists():
            log.warning("Save slot %s not found: %s", slot, path)
            return None
        try:
            return SaveData.from_json(path.read_text(encoding="utf-8"))
        except Exception:
            log.exception("Failed to load save slot %s", slot)
            return None

    def slot_info(self, slot: str) -> dict[str, str] | None:
        """Return lightweight info dict for displaying in the menu."""
        path = self._slot_path(slot)
        if not path.exists():
            self._invalidate_slot_info(slot)
            return None
        try:
            stat = path.stat()
            cache_key = stat.st_mtime_ns
            cached = self._slot_info_cache.get(slot)
            if cached and cached[0] == cache_key:
                return dict(cached[1])

            d = read_json_file(path)
            info = {
                "slot": slot,
                "timestamp": d.get("timestamp", ""),
                "round": str(d.get("round_number", 0)),
                "affection": str(d.get("affection", d.get("favor", 0))),
                "char": d.get("character_data", {}).get("name", "???"),
                "thumbnail_b64": d.get("thumbnail_b64") or "",
            }
            self._slot_info_cache[slot] = (cache_key, info)
            return dict(info)
        except Exception:
            self._invalidate_slot_info(slot)
            return None

    def restore_coordinator(self, data: SaveData, coordinator: GameCoordinator) -> None:
        """Push all fields from SaveData back into a GameCoordinator."""
        from phantom_seed.ai.protocol import CharacterProfile, SceneData

        # Restore state
        coordinator.seed_hash = data.seed_hash
        coordinator.atmosphere = data.atmosphere
        st = coordinator.state
        st.affection = data.affection
        st.heroine_affection = dict(data.heroine_affection)
        st.active_heroine = data.active_heroine
        st.route_phase = data.route_phase
        st.route_locked_to = data.route_locked_to
        st.round_number = data.round_number
        st.history = list(data.history)
        st.memory_fragments = list(data.memory_fragments)
        st.continuity_notes = list(data.continuity_notes)
        st.open_threads = list(data.open_threads)
        st.recent_locations = list(data.recent_locations)
        st.latest_hook = data.latest_hook
        st.is_ending = data.is_ending

        # Restore character
        if data.character_data:
            coordinator.character = CharacterProfile.model_validate(data.character_data)
        coordinator.character_sprite_path = (
            Path(data.character_sprite_path) if data.character_sprite_path else None
        )
        coordinator.heroines = [
            CharacterProfile.model_validate(item) for item in data.heroines_data
        ]
        coordinator.heroine_sprite_paths = {
            name: Path(path) for name, path in data.heroine_sprite_paths.items()
        }
        if coordinator.heroines:
            for heroine in coordinator.heroines:
                if heroine.name == st.active_heroine:
                    coordinator.character = heroine
                    coordinator.character_sprite_path = coordinator.heroine_sprite_paths.get(
                        heroine.name
                    )
                    break

        # Restore bg cache
        import threading

        coordinator._bg_cache = dict(data.bg_cache)
        if not hasattr(coordinator, "_bg_lock") or coordinator._bg_lock is None:
            coordinator._bg_lock = threading.Lock()

        # Restore current scene
        if data.current_scene_data:
            coordinator.current_scene = SceneData.model_validate(
                data.current_scene_data
            )
