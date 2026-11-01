from __future__ import annotations

from django.db.models import QuerySet

from apps.document_chunking.constants import ChunkEmbeddingStatus, VectorKind
from apps.document_chunking.models import ChunkEmbedding, ChunkingRun


def semantic_embeddings_for_chunking_run(chunking_run: ChunkingRun) -> QuerySet[ChunkEmbedding]:
    return (
        ChunkEmbedding.objects.filter(
            document_chunk__chunking_run=chunking_run,
            status=ChunkEmbeddingStatus.SUCCEEDED,
            vector_kind=VectorKind.SEMANTIC,
        )
        .select_related(
            'document_chunk',
            'document_chunk__document',
            'document_chunk__user',
            'document_chunk__business_model',
            'document_chunk__extraction_run',
        )
        .order_by('document_chunk__chunk_index')
    )
