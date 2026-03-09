from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MemoryWatchOptions:
    name: str | None = None
    enabled: bool = True
    capture_top_stats: bool = True


@dataclass(slots=True)
class MemoryWatchConfig:
    enabled: bool = True

    use_tracemalloc: bool = True
    tracemalloc_frames: int = 15
    top_stats_limit: int = 5

    force_gc_before: bool = False
    force_gc_after: bool = False

    leak_window: int = 8
    leak_min_growth_bytes: int = 1_500_000
    leak_min_retained_bytes: int = 300_000

    logger_name: str = "memory_watch"
    log_file_path: str = "logs/memory_watch.log"


@dataclass(slots=True)
class AllocationDiff:
    filename: str
    lineno: int
    size_diff: int
    count_diff: int


@dataclass(slots=True)
class MemoryMetric:
    endpoint: str
    method: str
    path: str
    status_code: int
    duration_ms: float

    rss_before: int
    rss_after: int
    rss_delta: int

    py_before: int | None = None
    py_after: int | None = None
    py_delta: int | None = None
    py_peak: int | None = None

    suspected_leak: bool = False
    leak_score: float = 0.0

    allocations: list[AllocationDiff] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)