from __future__ import annotations

from django.conf import settings

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.exceptions import ChunkingFailedError


def validate_chunk_drafts(
    drafts: list[ChunkDraft],
    *,
    config: ChunkingConfig,
) -> None:
    if not drafts:
        raise ChunkingFailedError('No chunks were produced.')

    seen_indexes: set[int] = set()
    max_provider_tokens = settings.EMBEDDING_MAX_INPUT_TOKENS

    for draft in drafts:
        if draft.chunk_index in seen_indexes:
            raise ChunkingFailedError(f'Duplicate chunk index: {draft.chunk_index}.')
        seen_indexes.add(draft.chunk_index)

        if not draft.content or not draft.content.strip():
            raise ChunkingFailedError(f'Chunk {draft.chunk_index} has empty content.')

        if draft.token_count <= 0:
            raise ChunkingFailedError(f'Chunk {draft.chunk_index} has invalid token count.')

        if draft.token_count > max_provider_tokens:
            raise ChunkingFailedError(
                f'Chunk {draft.chunk_index} exceeds embedding input token safety limit '
                f'({draft.token_count} > {max_provider_tokens}).'
            )

        if draft.token_count > config.prose_max_tokens * 2:
            raise ChunkingFailedError(
                f'Chunk {draft.chunk_index} exceeds configured chunk token maximum.'
            )
