from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings

from apps.document_chunking.models import DocumentChunk


@dataclass(frozen=True)
class RetrievalSourceReference:
    chunk_id: str
    document_id: str
    document_filename: str
    chunk_index: int
    score: float
    artifact_version: int
    content_hash: str


@dataclass(frozen=True)
class RetrievalContextChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    score: float
    element_type: str
    source_type: str
    truncated: bool = False


@dataclass(frozen=True)
class RetrievalContext:
    chunks: list[RetrievalContextChunk]
    sources: list[RetrievalSourceReference]
    truncation: dict = field(default_factory=dict)


def build_retrieval_context(
    *,
    ranked: list,
    chunks_by_id: dict[str, DocumentChunk],
) -> RetrievalContext:
    max_chunks = settings.RETRIEVAL_MAX_CONTEXT_CHUNKS
    max_chars = settings.RETRIEVAL_MAX_CONTEXT_CHARACTERS

    context_chunks: list[RetrievalContextChunk] = []
    sources: list[RetrievalSourceReference] = []
    total_chars = 0
    truncated = False
    truncated_reason = ''

    for hit in ranked:
        if len(context_chunks) >= max_chunks:
            truncated = True
            truncated_reason = 'max_context_chunks'
            break
        chunk = chunks_by_id.get(hit.chunk_id)
        if chunk is None:
            continue

        content = chunk.content
        content_truncated = False
        remaining = max_chars - total_chars
        if remaining <= 0:
            truncated = True
            truncated_reason = 'max_context_characters'
            break
        if len(content) > remaining:
            content = content[:remaining]
            content_truncated = True
            truncated = True
            truncated_reason = 'max_context_characters'

        context_chunks.append(
            RetrievalContextChunk(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                chunk_index=chunk.chunk_index,
                content=content,
                score=hit.score,
                element_type=chunk.element_type,
                source_type=chunk.source_type,
                truncated=content_truncated,
            )
        )
        sources.append(
            RetrievalSourceReference(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                document_filename=chunk.document.original_filename,
                chunk_index=chunk.chunk_index,
                score=hit.score,
                artifact_version=int(hit.payload.get('artifact_version') or 0),
                content_hash=chunk.content_hash,
            )
        )
        total_chars += len(content)
        if content_truncated:
            break

    truncation_meta = {
        'truncated': truncated,
        'reason': truncated_reason,
        'max_context_chunks': max_chunks,
        'max_context_characters': max_chars,
        'returned_chunks': len(context_chunks),
        'returned_characters': total_chars,
    }
    return RetrievalContext(chunks=context_chunks, sources=sources, truncation=truncation_meta)
