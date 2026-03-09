from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import MemoryMetric


def _to_mb(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value / 1024 / 1024:.2f} MB"


class HumanReadableFileSink:
    def __init__(self, log_file_path: str, logger_name: str = "memory_watch"):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = RotatingFileHandler(
                filename=self.log_file_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
            self.logger.addHandler(handler)

    def emit(self, metric: MemoryMetric) -> None:
        leak_text = "обнаружены" if metric.suspected_leak else "не обнаружены"

        lines = [
            f"[{metric.endpoint}] {metric.method} {metric.path} -> {metric.status_code}",
            f"Время выполнения: {metric.duration_ms:.2f} ms",
            "",
            f"Процесс до запроса занимал: {_to_mb(metric.rss_before)}",
            f"Процесс после запроса занимал: {_to_mb(metric.rss_after)}",
            f"Прирост памяти процесса: {_to_mb(metric.rss_delta)}",
            "",
            f"Python-объекты до запроса: {_to_mb(metric.py_before)}",
            f"Python-объекты после запроса: {_to_mb(metric.py_after)}",
            f"Удержанная память: {_to_mb(metric.py_delta)}",
            f"Пиковое потребление во время запроса: {_to_mb(metric.py_peak)}",
            "",
            f"Признаки утечки: {leak_text}",
            "-" * 100,
        ]

        self.logger.info("\n".join(lines))