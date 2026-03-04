"""Async generation pipeline — prefetch next segment in a background thread."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from phantom_seed.ai.protocol import SceneData

if TYPE_CHECKING:
    from phantom_seed.core.coordinator import GameCoordinator

log = logging.getLogger(__name__)


class AsyncPipeline:
    """Manages background prefetching of AI-generated content.

    Uses a single worker thread to generate the next scene while
    the player reads the current one. Pygame can't use asyncio
    easily, so we use threading instead.
    """

    def __init__(self, coordinator: GameCoordinator) -> None:
        self.coordinator = coordinator
        self._prefetched: SceneData | None = None
        self._error: Exception | None = None
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._generating = False

    @property
    def is_generating(self) -> bool:
        return self._generating

    @property
    def has_result(self) -> bool:
        with self._lock:
            return self._prefetched is not None or self._error is not None

    def request_next(self, player_choice: str = "", choice_delta: dict[str, int] | None = None) -> None:
        """Start generating the next scene in the background."""
        if self._generating:
            log.warning("Generation already in progress, ignoring request")
            return

        self._prefetched = None
        self._error = None
        self._generating = True

        self._worker = threading.Thread(
            target=self._generate_worker,
            args=(player_choice, choice_delta),
            daemon=True,
        )
        self._worker.start()

    def _generate_worker(self, player_choice: str, choice_delta: dict[str, int] | None) -> None:
        try:
            scene = self.coordinator.get_next_scene(player_choice, choice_delta)
            with self._lock:
                self._prefetched = scene
        except Exception as e:
            log.exception("Background generation failed")
            with self._lock:
                self._error = e
        finally:
            self._generating = False

    def collect(self) -> SceneData | None:
        """Collect the prefetched result. Returns None if not ready or failed."""
        with self._lock:
            if self._error:
                log.error("Prefetch had error: %s", self._error)
                self._error = None
                return None
            result = self._prefetched
            self._prefetched = None
            return result

    def wait(self, timeout: float = 30.0) -> SceneData | None:
        """Block until the prefetched result is ready."""
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=timeout)
        return self.collect()
