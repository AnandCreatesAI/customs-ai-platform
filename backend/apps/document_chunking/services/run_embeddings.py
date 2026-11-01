from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from apps.document_chunking.constants import (
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
    ChunkEmbeddingStatus,
)
from apps.document_chunking.exceptions import EmbeddingFailedError
from apps.document_chunking.models import ChunkEmbedding, ChunkingRun, DocumentChunk
from apps.document_chunking.serialization.vectors import serialize_float32_vector, validate_vector_payload
from apps.document_chunking.services.ownership import validate_chunk_row, validate_embedding_row
from apps.training_jobs.models import TrainingJob, TrainingJobStatus
from gateways.embeddings.factory import get_embedding_gateway
from gateways.embeddings.interfaces import EmbeddingRequest

logger = logging.getLogger(__name__)


def _ensure_not_cancelled(job: TrainingJob) -> None:
    job.refresh_from_db()
    if job.status == TrainingJobStatus.CANCELLED:
        raise EmbeddingFailedError('Training job was cancelled.')


def _model_version_for_provider(provider) -> str:
    return provider.model_version


def run_embeddings_for_chunking_run(
    *,
    job: TrainingJob,
    chunking_run: ChunkingRun,
    progress_callback=None,
) -> None:
    _ensure_not_cancelled(job)

    gateway = get_embedding_gateway()
    provider = gateway.provider
    model_name = provider.model_name
    model_version = _model_version_for_provider(provider)
    dimension = provider.default_dimension

    chunks = list(
        DocumentChunk.objects.filter(chunking_run=chunking_run)
        .select_related('document', 'user', 'business_model')
        .order_by('chunk_index')
    )
    if not chunks:
        raise EmbeddingFailedError('No chunks available for embedding.')

    pending: list[DocumentChunk] = []
    for chunk in chunks:
        validate_chunk_row(chunk=chunk)
        existing = ChunkEmbedding.objects.filter(
            document_chunk=chunk,
            embedding_model=model_name,
            embedding_model_version=model_version,
        ).first()
        if existing and existing.status == ChunkEmbeddingStatus.SUCCEEDED:
            continue
        pending.append(chunk)

    if not pending and progress_callback:
        progress_callback(stage='embed_complete', progress=95)
        return

    batch_size = settings.EMBEDDING_BATCH_SIZE
    processed = 0
    total = len(pending)

    for offset in range(0, total, batch_size):
        _ensure_not_cancelled(job)
        batch = pending[offset : offset + batch_size]
        texts = [chunk.content for chunk in batch]
        try:
            response = gateway.embed_texts(EmbeddingRequest(texts=texts))
        except Exception as exc:
            raise EmbeddingFailedError(f'Embedding provider failed: {exc}') from exc

        if len(response.vectors) != len(batch):
            raise EmbeddingFailedError('Embedding provider returned an incomplete batch.')

        if response.dimension != dimension:
            raise EmbeddingFailedError('Embedding dimension mismatch from provider response.')

        with transaction.atomic():
            for chunk, vector in zip(batch, response.vectors, strict=True):
                if len(vector.values) != dimension:
                    raise EmbeddingFailedError(
                        f'Vector dimension mismatch for chunk {chunk.chunk_index}.'
                    )
                payload = serialize_float32_vector(vector.values)
                validate_vector_payload(
                    payload,
                    dimension=dimension,
                    serialization_version=VECTOR_SERIALIZATION_VERSION,
                    dtype=VECTOR_DTYPE_FLOAT32,
                )
                embedding, _created = ChunkEmbedding.objects.update_or_create(
                    document_chunk=chunk,
                    embedding_model=model_name,
                    embedding_model_version=model_version,
                    defaults={
                        'provider_name': response.provider_name,
                        'vector_kind': vector.vector_kind,
                        'embedding_dimension': dimension,
                        'dtype': VECTOR_DTYPE_FLOAT32,
                        'serialization_version': VECTOR_SERIALIZATION_VERSION,
                        'vector_payload': payload,
                        'content_hash': chunk.content_hash,
                        'status': ChunkEmbeddingStatus.SUCCEEDED,
                        'error_message': '',
                    },
                )
                validate_embedding_row(embedding=embedding)

        processed += len(batch)
        if progress_callback and total:
            embed_progress = 70 + int(25 * (processed / total))
            progress_callback(stage='embed', progress=min(embed_progress, 95))

    failed = ChunkEmbedding.objects.filter(
        document_chunk__chunking_run=chunking_run,
        status=ChunkEmbeddingStatus.FAILED,
    ).exists()
    if failed:
        raise EmbeddingFailedError('One or more chunk embeddings failed.')

    for chunk in chunks:
        if not ChunkEmbedding.objects.filter(
            document_chunk=chunk,
            embedding_model=model_name,
            embedding_model_version=model_version,
            status=ChunkEmbeddingStatus.SUCCEEDED,
        ).exists():
            raise EmbeddingFailedError('Not all chunks received successful embeddings.')

    if progress_callback:
        progress_callback(stage='embed_complete', progress=95)

    logger.info(
        'embedding_succeeded job_id=%s chunking_run_id=%s chunks=%s provider=%s',
        job.id,
        chunking_run.id,
        len(chunks),
        provider.provider_name,
    )
