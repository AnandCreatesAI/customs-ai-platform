from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedHit:
    chunk_id: str
    document_id: str
    score: float
    payload: dict


def rank_and_deduplicate_hits(
    hits: list[RankedHit],
    *,
    min_score: float | None,
    top_k: int,
) -> list[RankedHit]:
    filtered = hits
    if min_score is not None:
        filtered = [hit for hit in hits if hit.score >= min_score]

    by_chunk: dict[str, RankedHit] = {}
    for hit in sorted(filtered, key=lambda item: item.score, reverse=True):
        existing = by_chunk.get(hit.chunk_id)
        if existing is None or hit.score > existing.score:
            by_chunk[hit.chunk_id] = hit

    ordered = sorted(by_chunk.values(), key=lambda item: item.score, reverse=True)
    return ordered[:top_k]
