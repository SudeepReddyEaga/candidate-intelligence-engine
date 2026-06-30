from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


@contextmanager
def measure_ms(metrics: dict[str, float], name: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        metrics[name] = round((perf_counter() - start) * 1000, 3)
