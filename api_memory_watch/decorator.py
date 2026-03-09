from __future__ import annotations

from .config import MemoryWatchOptions


def memory_watch(
    name: str | None = None,
    *,
    enabled: bool = True,
    capture_top_stats: bool = True,
):
    def decorator(func):
        setattr(
            func,
            "__memory_watch__",
            MemoryWatchOptions(
                name=name,
                enabled=enabled,
                capture_top_stats=capture_top_stats,
            ),
        )
        return func

    return decorator