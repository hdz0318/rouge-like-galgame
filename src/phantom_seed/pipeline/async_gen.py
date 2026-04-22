"""Async generation pipeline — prefetch next segment in a background thread."""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import TYPE_CHECKING
from typing import Callable

from phantom_seed.ai.protocol import SceneData

if TYPE_CHECKING:
    from phantom_seed.core.coordinator import GameCoordinator

log = logging.getLogger(__name__)


class _TerminalProgressBar:
    """Single-line terminal progress bar, inspired by pip style output."""

    def __init__(self, title: str, total: int) -> None:
        self.title = title
        self.total = max(1, total)
        self.width = 28
        self.message_width = 44
        self._lock = threading.Lock()
        self._started_at = time.time()

    def update(self, step: int, message: str = "") -> None:
        with self._lock:
            step = min(max(step, 0), self.total)
            ratio = step / self.total
            percent = int(ratio * 100)
            filled = int(self.width * ratio)
            bar = "#" * filled + "-" * (self.width - filled)
            elapsed = time.time() - self._started_at
            clipped = message[: self.message_width].ljust(self.message_width)
            line = (
                f"\r{self.title:<8} |{bar}| {percent:>3d}% "
                f"{elapsed:>6.1f}s {clipped}"
            )
            print(line, end="", file=sys.stdout, flush=True)

    def close(self, ok: bool, message: str) -> None:
        with self._lock:
            final = self.total if ok else max(0, self.total - 1)
            ratio = final / self.total
            percent = int(ratio * 100)
            filled = int(self.width * ratio)
            bar = "#" * filled + "-" * (self.width - filled)
            elapsed = time.time() - self._started_at
            clipped = message[: self.message_width].ljust(self.message_width)
            line = (
                f"\r{self.title:<8} |{bar}| {percent:>3d}% "
                f"{elapsed:>6.1f}s {clipped}"
            )
            print(line, end="", file=sys.stdout, flush=True)
            print(file=sys.stdout, flush=True)


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
        self._request_id = 0
        self._progress_bar: _TerminalProgressBar | None = None
        self._progress_total = 0
        self._progress_title = ""
        self._progress_step = 0
        self._progress_message = ""
        self._progress_started_at = 0.0

    @property
    def is_generating(self) -> bool:
        with self._lock:
            return self._generating

    @property
    def has_result(self) -> bool:
        with self._lock:
            return self._prefetched is not None or self._error is not None

    def _start_progress(self, title: str, total: int) -> None:
        with self._lock:
            self._progress_total = max(1, total)
            self._progress_title = title
            self._progress_step = 0
            self._progress_message = "开始"
            self._progress_started_at = time.time()
            self._progress_bar = _TerminalProgressBar(title, self._progress_total)
            progress_bar = self._progress_bar
        assert progress_bar is not None
        progress_bar.update(0, "开始")

    def _on_progress(self, step: int, total: int, message: str) -> None:
        with self._lock:
            current_total = self._progress_total
            current_bar = self._progress_bar
        if total != current_total or current_bar is None:
            self._start_progress("生成中", total)
        with self._lock:
            self._progress_step = min(max(step, 0), max(1, total))
            self._progress_message = message
            progress_bar = self._progress_bar
        assert progress_bar is not None
        progress_bar.update(step, message)

    def _finish_progress(self, ok: bool, message: str) -> None:
        with self._lock:
            progress_bar = self._progress_bar
            total = self._progress_total
            self._progress_step = total if ok else max(0, total - 1)
            self._progress_message = message
            self._progress_bar = None
        if progress_bar is not None:
            progress_bar.close(ok=ok, message=message)

    def get_progress_snapshot(self) -> dict[str, object]:
        with self._lock:
            total = max(1, self._progress_total)
            started_at = self._progress_started_at
            title = self._progress_title or "生成中"
            step = min(max(self._progress_step, 0), total)
            message = self._progress_message or "准备中"
            is_generating = self._generating
        elapsed = max(0.0, time.time() - started_at) if started_at else 0.0
        return {
            "title": title,
            "step": step,
            "total": total,
            "message": message,
            "elapsed": elapsed,
            "is_generating": is_generating,
        }

    def reset(self) -> None:
        """Drop any pending result/error and advance the request generation."""
        progress_bar: _TerminalProgressBar | None
        with self._lock:
            self._request_id += 1
            self._prefetched = None
            self._error = None
            self._generating = False
            self._progress_total = 0
            self._progress_title = ""
            self._progress_step = 0
            self._progress_message = ""
            self._progress_started_at = 0.0
            progress_bar = self._progress_bar
            self._progress_bar = None
        if progress_bar is not None:
            progress_bar.close(ok=False, message="已取消")

    def shutdown(self, timeout: float = 0.1) -> None:
        """Invalidate the current request and briefly join the worker if possible."""
        worker = self._worker
        self.reset()
        if worker and worker.is_alive():
            worker.join(timeout=timeout)

    def request_init(self, seed: str) -> None:
        """Start game initialization in the background with terminal progress."""
        with self._lock:
            if self._generating:
                log.warning("Generation already in progress, ignoring init request")
                return
            self._request_id += 1
            request_id = self._request_id
            self._prefetched = None
            self._error = None
            self._generating = True
        self._start_progress("初始化", 5)

        self._worker = threading.Thread(
            target=self._init_worker,
            args=(seed, request_id),
            daemon=True,
        )
        self._worker.start()

    def request_next(
        self, player_choice: str = "", choice_delta: dict[str, int] | None = None
    ) -> None:
        """Start generating the next scene in the background."""
        with self._lock:
            if self._generating:
                log.warning("Generation already in progress, ignoring request")
                return
            self._request_id += 1
            request_id = self._request_id
            self._prefetched = None
            self._error = None
            self._generating = True
        self._start_progress("生成中", 6)

        self._worker = threading.Thread(
            target=self._generate_worker,
            args=(player_choice, choice_delta, request_id),
            daemon=True,
        )
        self._worker.start()

    def _is_active_request(self, request_id: int) -> bool:
        with self._lock:
            return request_id == self._request_id

    def _progress_callback(self, request_id: int) -> Callable[[int, int, str], None]:
        def callback(step: int, total: int, message: str) -> None:
            if not self._is_active_request(request_id):
                return
            self._on_progress(step, total, message)

        return callback

    def _init_worker(self, seed: str, request_id: int) -> None:
        ok = False
        try:
            scene = self.coordinator.init_game(
                seed,
                progress_cb=self._progress_callback(request_id),
            )
            if self._is_active_request(request_id):
                with self._lock:
                    self._prefetched = scene
                ok = True
        except Exception as e:
            log.exception("Background init failed")
            if self._is_active_request(request_id):
                with self._lock:
                    self._error = e
        finally:
            if self._is_active_request(request_id):
                with self._lock:
                    self._generating = False
                self._finish_progress(ok, "完成" if ok else "失败")

    def _generate_worker(
        self,
        player_choice: str,
        choice_delta: dict[str, int] | None,
        request_id: int,
    ) -> None:
        ok = False
        try:
            scene = self.coordinator.get_next_scene(
                player_choice,
                choice_delta,
                progress_cb=self._progress_callback(request_id),
            )
            if self._is_active_request(request_id):
                with self._lock:
                    self._prefetched = scene
                ok = True
        except Exception as e:
            log.exception("Background generation failed")
            if self._is_active_request(request_id):
                with self._lock:
                    self._error = e
        finally:
            if self._is_active_request(request_id):
                with self._lock:
                    self._generating = False
                self._finish_progress(ok, "完成" if ok else "失败")

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
