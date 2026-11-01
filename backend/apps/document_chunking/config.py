from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ChunkingConfig:
    prose_target_tokens: int
    prose_min_tokens: int
    prose_max_tokens: int
    prose_overlap_tokens: int
    spreadsheet_min_rows: int
    spreadsheet_max_rows: int
    json_max_tokens: int
    max_chunks_per_document: int
    chunking_version: str
    db_batch_size: int


def get_chunking_config() -> ChunkingConfig:
    return ChunkingConfig(
        prose_target_tokens=settings.CHUNKING_PROSE_TARGET_TOKENS,
        prose_min_tokens=settings.CHUNKING_PROSE_MIN_TOKENS,
        prose_max_tokens=settings.CHUNKING_PROSE_MAX_TOKENS,
        prose_overlap_tokens=settings.CHUNKING_PROSE_OVERLAP_TOKENS,
        spreadsheet_min_rows=settings.CHUNKING_SPREADSHEET_MIN_ROWS,
        spreadsheet_max_rows=settings.CHUNKING_SPREADSHEET_MAX_ROWS,
        json_max_tokens=settings.CHUNKING_JSON_MAX_TOKENS,
        max_chunks_per_document=settings.CHUNKING_MAX_CHUNKS_PER_DOCUMENT,
        chunking_version=settings.CHUNKING_VERSION,
        db_batch_size=settings.CHUNKING_DB_BATCH_SIZE,
    )
