from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.document_chunking.models import ChunkEmbedding, DocumentChunk


def build_point_payload(
    *,
    chunk: DocumentChunk,
    embedding: ChunkEmbedding,
    business_model_key: str,
    artifact_version: int,
    is_active: bool,
) -> dict[str, Any]:
    return {
        'chunk_id': str(chunk.id),
        'document_id': str(chunk.document_id),
        'user_id': str(chunk.user_id),
        'business_model_id': str(chunk.business_model_id),
        'business_model_key': business_model_key,
        'extraction_run_id': str(chunk.extraction_run_id),
        'artifact_version': artifact_version,
        'chunking_run_id': str(chunk.chunking_run_id),
        'chunking_version': chunk.chunking_version,
        'chunk_index': chunk.chunk_index,
        'visibility': chunk.visibility,
        'source_type': chunk.source_type,
        'element_type': chunk.element_type,
        'content_hash': chunk.content_hash,
        'embedding_model': embedding.embedding_model,
        'embedding_model_version': embedding.embedding_model_version,
        'vector_kind': embedding.vector_kind,
        'is_active': is_active,
        'indexed_at': datetime.now(timezone.utc).isoformat(),
    }
