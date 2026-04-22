from __future__ import annotations

import time

from phantom_seed.pipeline.async_gen import AsyncPipeline


class _SlowCoordinator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def init_game(self, seed: str, *, progress_cb=None):  # noqa: ANN001
        self.calls.append(seed)
        if progress_cb:
            progress_cb(1, 5, f"seed:{seed}")
        time.sleep(0.05 if seed == "first" else 0.01)
        return {"seed": seed}


def test_reset_discards_stale_worker_result() -> None:
    coordinator = _SlowCoordinator()
    pipeline = AsyncPipeline(coordinator)  # type: ignore[arg-type]

    pipeline.request_init("first")
    time.sleep(0.01)
    pipeline.reset()
    pipeline.request_init("second")

    result = pipeline.wait(timeout=1.0)

    assert result == {"seed": "second"}

