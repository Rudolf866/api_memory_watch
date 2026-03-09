from __future__ import annotations

import gc
import os
import time
import tracemalloc

import psutil
from fastapi import Request
from fastapi.routing import APIRoute

from .config import AllocationDiff, MemoryMetric, MemoryWatchConfig
from .detector import LeakDetector
from .sinks import HumanReadableFileSink


class MemoryWatchManager:
    def __init__(self, config: MemoryWatchConfig | None = None, sink=None):
        self.config = config or MemoryWatchConfig()
        self.process = psutil.Process(os.getpid())
        self.detector = LeakDetector(
            window=self.config.leak_window,
            min_growth_bytes=self.config.leak_min_growth_bytes,
            min_retained_bytes=self.config.leak_min_retained_bytes,
        )

        self.sink = sink or HumanReadableFileSink(
            log_file_path=self.config.log_file_path,
            logger_name=self.config.logger_name,
        )

        if self.config.use_tracemalloc and not tracemalloc.is_tracing():
            tracemalloc.start(self.config.tracemalloc_frames)

    async def profile_request(self, request: Request, handler, options):
        if not self.config.enabled or not options.enabled:
            return await handler(request)

        if self.config.force_gc_before:
            gc.collect()

        rss_before = self.process.memory_info().rss

        py_before = None
        py_peak = None
        snapshot_before = None

        if self.config.use_tracemalloc:
            py_before, _ = tracemalloc.get_traced_memory()
            if options.capture_top_stats:
                snapshot_before = tracemalloc.take_snapshot()

        started_at = time.perf_counter()
        response = None

        try:
            response = await handler(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 3)

            if self.config.force_gc_after:
                gc.collect()

            rss_after = self.process.memory_info().rss
            rss_delta = rss_after - rss_before

            py_after = None
            py_delta = None
            allocations = []

            if self.config.use_tracemalloc:
                py_after, py_peak = tracemalloc.get_traced_memory()
                if py_before is not None:
                    py_delta = py_after - py_before

                if snapshot_before and options.capture_top_stats:
                    snapshot_after = tracemalloc.take_snapshot()
                    for stat in snapshot_after.compare_to(
                        snapshot_before, "lineno"
                    )[: self.config.top_stats_limit]:
                        if not stat.traceback:
                            continue
                        frame = stat.traceback[0]
                        allocations.append(
                            AllocationDiff(
                                filename=frame.filename,
                                lineno=frame.lineno,
                                size_diff=stat.size_diff,
                                count_diff=stat.count_diff,
                            )
                        )

            endpoint_name = options.name or f"{request.method} {request.url.path}"
            retained = py_delta if py_delta is not None else rss_delta

            suspected_leak, leak_score = self.detector.evaluate(
                endpoint=endpoint_name,
                retained_bytes=retained,
            )

            metric = MemoryMetric(
                endpoint=endpoint_name,
                method=request.method,
                path=request.url.path,
                status_code=getattr(response, "status_code", 500),
                duration_ms=duration_ms,
                rss_before=rss_before,
                rss_after=rss_after,
                rss_delta=rss_delta,
                py_before=py_before,
                py_after=py_after,
                py_delta=py_delta,
                py_peak=py_peak,
                suspected_leak=suspected_leak,
                leak_score=leak_score,
                allocations=allocations,
            )

            self.sink.emit(metric)


class MemoryWatchRoute(APIRoute):
    manager: MemoryWatchManager | None = None

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()
        options = getattr(self.endpoint, "__memory_watch__", None)

        if options is None:
            return original_route_handler

        async def custom_route_handler(request: Request):
            manager = self.manager
            if manager is None:
                return await original_route_handler(request)

            return await manager.profile_request(
                request=request,
                handler=original_route_handler,
                options=options,
            )

        return custom_route_handler


def configure_memory_watch(
    config: MemoryWatchConfig | None = None,
    sink=None,
) -> MemoryWatchManager:
    manager = MemoryWatchManager(config=config, sink=sink)
    MemoryWatchRoute.manager = manager
    return manager