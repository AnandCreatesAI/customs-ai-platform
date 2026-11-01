from __future__ import annotations


def average_confidence(scores: list[float]) -> float | None:
    if not scores:
        return None
    return sum(scores) / len(scores)
