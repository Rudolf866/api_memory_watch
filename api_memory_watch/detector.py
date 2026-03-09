from __future__ import annotations

from collections import defaultdict, deque
from statistics import mean


class LeakDetector:
    def __init__(
        self,
        window: int = 8,
        min_growth_bytes: int = 1_500_000,
        min_retained_bytes: int = 300_000,
    ):
        self.window = window
        self.min_growth_bytes = min_growth_bytes
        self.min_retained_bytes = min_retained_bytes
        self._history: dict[str, deque[int]] = defaultdict(
            lambda: deque(maxlen=self.window)
        )

    def evaluate(self, endpoint: str, retained_bytes: int) -> tuple[bool, float]:
        history = self._history[endpoint]
        history.append(retained_bytes)

        if len(history) < self.window:
            return False, 0.0

        values = list(history)
        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        first_avg = mean(first_half)
        second_avg = mean(second_half)
        growth = second_avg - first_avg

        positive_tail = sum(v > self.min_retained_bytes for v in second_half)
        mostly_growing = sum(
            1 for a, b in zip(values, values[1:]) if b >= a
        ) >= len(values) - 2

        suspected = (
            growth >= self.min_growth_bytes
            and positive_tail >= max(2, len(second_half) - 1)
            and mostly_growing
        )

        score = max(0.0, min(1.0, growth / max(self.min_growth_bytes * 2, 1)))
        return suspected, round(score, 3)