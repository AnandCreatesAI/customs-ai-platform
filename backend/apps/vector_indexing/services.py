from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.document_chunking.constants import (
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
    VectorKind,
)
from apps.document_chunking.models import ChunkingRunStatus
from apps.document_chunking.serialization.vectors import deserialize_float32_vector
from apps.knowledge.models import KnowledgeIndexingStatus
from apps.knowledge.services import get_or_create_document_knowledge_source, knowledge_sources_for_document
from apps.training_jobs.models import TrainingJob, TrainingJobStatus
from apps.vector_indexing.constants import (
    SKIP_REASON_SEMANTIC_UNAVAILABLE,
    ACTIVE_INDEXING_STATUSES,
    DISPATCHABLE_INDEXING_STATUSES,
    ChunkVectorIndexStatus,
    IndexingActivationPhase,
    IndexingRunStatus,
)
from apps.vector_indexing.models import ChunkVectorIndex, DocumentIndexActivation, IndexingRun
from apps.vector_indexing.selectors import semantic_embeddings_for_chunking_run
from gateways.qdrant.config import resolve_collection_name
from gateways.qdrant.exceptions import QdrantGatewayError, QdrantUnavailableError
from gateways.qdrant.factory import get_qdrant_gateway
from gateways.qdrant.interfaces import QdrantPoint
from gateways.qdrant.payload import build_point_payload

logger = logging.getLogger(__name__)


class IndexingServiceError(Exception):
    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.transient = transient


def _validate_training_job(job: TrainingJob) -> None:
    if job.status != TrainingJobStatus.COMPLETED:
        raise IndexingServiceError('Training job must be completed before indexing.')
    document = job.document
    if document.user_id != job.user_id:
        raise IndexingServiceError('Training job user mismatch.')
    if document.business_model_id != job.business_model_id:
        raise IndexingServiceError('Training job business model mismatch.')


def _embedding_config_filter(
    *,
    chunking_run_id,
    dimension: int,
    embedding_model: str,
    embedding_model_version: str,
):
    return {
        'chunking_run_id': chunking_run_id,
        'embedding_dimension': dimension,
        'embedding_model': embedding_model,
        'embedding_model_version': embedding_model_version,
    }


def _find_successful_indexing_run(
    *,
    chunking_run_id,
    dimension: int,
    embedding_model: str,
    embedding_model_version: str,
) -> IndexingRun | None:
    return IndexingRun.objects.filter(
        **_embedding_config_filter(
            chunking_run_id=chunking_run_id,
            dimension=dimension,
            embedding_model=embedding_model,
            embedding_model_version=embedding_model_version,
        ),
        status=IndexingRunStatus.COMPLETED,
    ).first()


@transaction.atomic
def prepare_indexing_run(*, training_job: TrainingJob) -> IndexingRun:
    _validate_training_job(training_job)
    extraction_run = getattr(training_job, 'extraction_run', None)
    if extraction_run is None:
        raise IndexingServiceError('Training job has no extraction run.')
    chunking_run = getattr(extraction_run, 'chunking_run', None)
    if chunking_run is None or chunking_run.status != ChunkingRunStatus.SUCCEEDED:
        raise IndexingServiceError('Training job has no successful chunking run.')

    semantic = semantic_embeddings_for_chunking_run(chunking_run)
    if not semantic.exists():
        run = IndexingRun.objects.create(
            training_job=training_job,
            document=training_job.document,
            user=training_job.user,
            business_model=training_job.business_model,
            extraction_run=extraction_run,
            chunking_run=chunking_run,
            artifact_version=extraction_run.artifact_version,
            embedding_dimension=0,
            status=IndexingRunStatus.SKIPPED,
            skip_reason=SKIP_REASON_SEMANTIC_UNAVAILABLE,
            completed_at=datetime.now(timezone.utc),
        )
        get_or_create_document_knowledge_source(training_job=training_job)
        _update_knowledge_sources(
            document_id=training_job.document_id,
            business_model_id=training_job.business_model_id,
            indexing_status=KnowledgeIndexingStatus.PENDING,
        )
        return run

    first = semantic.first()
    dimension = first.embedding_dimension
    embedding_model = first.embedding_model
    embedding_model_version = first.embedding_model_version
    collection_name = resolve_collection_name(
        business_model_key=training_job.business_model.key,
        dimension=dimension,
    )

    config = _embedding_config_filter(
        chunking_run_id=chunking_run.pk,
        dimension=dimension,
        embedding_model=embedding_model,
        embedding_model_version=embedding_model_version,
    )

    successful = _find_successful_indexing_run(
        chunking_run_id=chunking_run.pk,
        dimension=dimension,
        embedding_model=embedding_model,
        embedding_model_version=embedding_model_version,
    )
    if successful:
        return successful

    existing_active = (
        IndexingRun.objects.select_for_update()
        .filter(**config, status__in=ACTIVE_INDEXING_STATUSES)
        .first()
    )
    if existing_active:
        return existing_active

    failed_retryable = (
        IndexingRun.objects.select_for_update()
        .filter(**config, status=IndexingRunStatus.FAILED)
        .order_by('-created_at')
        .first()
    )
    if failed_retryable is not None:
        failed_retryable.status = IndexingRunStatus.QUEUED
        failed_retryable.error_message = ''
        failed_retryable.dispatch_error = ''
        failed_retryable.completed_at = None
        failed_retryable.save(
            update_fields=[
                'status',
                'error_message',
                'dispatch_error',
                'completed_at',
                'updated_at',
            ]
        )
        get_or_create_document_knowledge_source(training_job=training_job)
        return failed_retryable

    try:
        run = IndexingRun.objects.create(
            training_job=training_job,
            document=training_job.document,
            user=training_job.user,
            business_model=training_job.business_model,
            extraction_run=extraction_run,
            chunking_run=chunking_run,
            artifact_version=extraction_run.artifact_version,
            embedding_dimension=dimension,
            embedding_model=embedding_model,
            embedding_model_version=embedding_model_version,
            collection_name=collection_name,
            status=IndexingRunStatus.QUEUED,
            total_chunks=semantic.count(),
        )
    except IntegrityError:
        existing = (
            IndexingRun.objects.filter(**config)
            .exclude(status=IndexingRunStatus.SKIPPED)
            .order_by('-created_at')
            .first()
        )
        if existing is None:
            raise
        return existing

    get_or_create_document_knowledge_source(training_job=training_job)
    return run


def _vector_from_embedding(embedding) -> list[float]:
    if embedding.vector_kind != VectorKind.SEMANTIC:
        raise IndexingServiceError('Non-semantic embedding cannot be indexed.')
    return deserialize_float32_vector(
        bytes(embedding.vector_payload),
        dimension=embedding.embedding_dimension,
        serialization_version=embedding.serialization_version,
        dtype=embedding.dtype or VECTOR_DTYPE_FLOAT32,
    )


def _resolve_knowledge_indexing_status(*, document_id, business_model_id) -> str:
    activation = DocumentIndexActivation.objects.filter(
        document_id=document_id,
        business_model_id=business_model_id,
    ).first()
    if activation and activation.active_collection_name:
        return KnowledgeIndexingStatus.INDEXED
    return KnowledgeIndexingStatus.PENDING


def _update_knowledge_sources(
    *,
    document_id,
    business_model_id,
    indexing_status: str,
    vector_store: str = '',
) -> None:
    sources = knowledge_sources_for_document(
        document_id=document_id,
        business_model_id=business_model_id,
    )
    for source in sources:
        source.indexing_status = indexing_status
        if vector_store:
            source.vector_store = vector_store
        source.save(update_fields=['indexing_status', 'vector_store', 'updated_at'])


def _load_semantic_embeddings(chunking_run):
    return list(semantic_embeddings_for_chunking_run(chunking_run))


def _build_points_for_embeddings(
    *,
    run: IndexingRun,
    embeddings: list,
    vectors: list[list[float]],
    is_active: bool,
) -> list[QdrantPoint]:
    business_model_key = run.business_model.key
    artifact_version = run.artifact_version
    points: list[QdrantPoint] = []
    for embedding, vector in zip(embeddings, vectors, strict=True):
        chunk = embedding.document_chunk
        payload = build_point_payload(
            chunk=chunk,
            embedding=embedding,
            business_model_key=business_model_key,
            artifact_version=artifact_version,
            is_active=is_active,
        )
        points.append(QdrantPoint(point_id=str(chunk.id), vector=vector, payload=payload))
    return points


def _record_pending_activation(*, run: IndexingRun) -> DocumentIndexActivation:
    with transaction.atomic():
        activation, _created = DocumentIndexActivation.objects.select_for_update().get_or_create(
            document_id=run.document_id,
            business_model_id=run.business_model_id,
            defaults={
                'active_artifact_version': 0,
                'active_collection_name': '',
            },
        )
        if activation.pending_indexing_run_id and activation.pending_indexing_run_id != run.pk:
            raise IndexingServiceError(
                'Another indexing run is already pending activation for this document.'
            )
        activation.pending_indexing_run = run
        activation.pending_artifact_version = run.artifact_version
        activation.pending_collection_name = run.collection_name
        activation.pending_since = datetime.now(timezone.utc)
        activation.save(
            update_fields=[
                'pending_indexing_run',
                'pending_artifact_version',
                'pending_collection_name',
                'pending_since',
                'updated_at',
            ]
        )
    return activation


def _clear_pending_activation(*, document_id, business_model_id, run_id) -> None:
    with transaction.atomic():
        activation = (
            DocumentIndexActivation.objects.select_for_update()
            .filter(document_id=document_id, business_model_id=business_model_id)
            .first()
        )
        if activation is None:
            return
        if str(activation.pending_indexing_run_id) != str(run_id):
            return
        activation.pending_indexing_run = None
        activation.pending_artifact_version = None
        activation.pending_collection_name = ''
        activation.pending_since = None
        activation.save(
            update_fields=[
                'pending_indexing_run',
                'pending_artifact_version',
                'pending_collection_name',
                'pending_since',
                'updated_at',
            ]
        )


def _commit_activation_from_pending(*, activation: DocumentIndexActivation, run: IndexingRun) -> None:
    if activation.pending_indexing_run_id != run.pk:
        raise IndexingServiceError('Pending activation does not match indexing run.')
    activation.active_artifact_version = run.artifact_version
    activation.active_indexing_run = run
    activation.active_collection_name = run.collection_name
    activation.activated_at = datetime.now(timezone.utc)
    activation.pending_indexing_run = None
    activation.pending_artifact_version = None
    activation.pending_collection_name = ''
    activation.pending_since = None
    activation.save(
        update_fields=[
            'active_artifact_version',
            'active_indexing_run',
            'active_collection_name',
            'activated_at',
            'pending_indexing_run',
            'pending_artifact_version',
            'pending_collection_name',
            'pending_since',
            'updated_at',
        ]
    )


def _activate_qdrant_for_run(
    *,
    gateway,
    run: IndexingRun,
    embeddings: list,
    previous_artifact: int | None,
    previous_collection: str,
    batch_size: int,
) -> None:
    artifact_version = run.artifact_version
    for offset in range(0, len(embeddings), batch_size):
        batch = embeddings[offset : offset + batch_size]
        vectors = [_vector_from_embedding(embedding) for embedding in batch]
        active_points = _build_points_for_embeddings(
            run=run,
            embeddings=batch,
            vectors=vectors,
            is_active=True,
        )
        gateway.upsert_points(collection_name=run.collection_name, points=active_points)

    if previous_artifact is not None and previous_artifact != artifact_version and previous_collection:
        if previous_collection != run.collection_name:
            gateway.set_payload_by_filter(
                collection_name=previous_collection,
                payload={'is_active': False},
                document_id=str(run.document_id),
                artifact_version=previous_artifact,
            )
        else:
            gateway.set_payload_by_filter(
                collection_name=previous_collection,
                payload={'is_active': False},
                document_id=str(run.document_id),
                artifact_version=previous_artifact,
            )


def _mark_run_failed(
    run: IndexingRun,
    *,
    message: str,
    indexed: int | None = None,
    failed: int | None = None,
    clear_pending: bool = True,
) -> None:
    run.status = IndexingRunStatus.FAILED
    run.error_message = message
    run.completed_at = datetime.now(timezone.utc)
    update_fields = ['status', 'error_message', 'completed_at', 'updated_at']
    if indexed is not None:
        run.indexed_chunks = indexed
        update_fields.append('indexed_chunks')
    if failed is not None:
        run.failed_chunks = failed
        update_fields.append('failed_chunks')
    run.save(update_fields=update_fields)
    if clear_pending:
        _clear_pending_activation(
            document_id=run.document_id,
            business_model_id=run.business_model_id,
            run_id=run.pk,
        )
    ks_status = _resolve_knowledge_indexing_status(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
    )
    activation = DocumentIndexActivation.objects.filter(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
    ).first()
    vector_store = activation.active_collection_name if activation else ''
    final_status = (
        KnowledgeIndexingStatus.INDEXED
        if ks_status == KnowledgeIndexingStatus.INDEXED
        else KnowledgeIndexingStatus.FAILED
    )
    _update_knowledge_sources(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
        indexing_status=final_status,
        vector_store=vector_store,
    )


def _mark_transient_failure(run: IndexingRun, exc: Exception) -> None:
    run.status = IndexingRunStatus.RETRYING
    run.retry_count = min(run.retry_count + 1, 32767)
    run.error_message = str(exc)[:2000]
    run.save(update_fields=['status', 'retry_count', 'error_message', 'updated_at'])


def run_indexing_run(indexing_run_id: str) -> None:
    if not settings.QDRANT_INDEXING_ENABLED:
        raise IndexingServiceError('Qdrant indexing is disabled.')

    with transaction.atomic():
        run = (
            IndexingRun.objects.select_for_update()
            .select_related(
                'training_job',
                'document',
                'business_model',
                'extraction_run',
                'chunking_run',
            )
            .get(pk=indexing_run_id)
        )
        if run.status == IndexingRunStatus.SKIPPED:
            return
        if run.status == IndexingRunStatus.COMPLETED:
            return
        if run.status not in DISPATCHABLE_INDEXING_STATUSES:
            raise IndexingServiceError(f'Indexing run is not dispatchable: {run.status}')

        run.status = IndexingRunStatus.PROCESSING
        run.started_at = run.started_at or datetime.now(timezone.utc)
        run.error_message = ''
        run.save(update_fields=['status', 'started_at', 'error_message', 'updated_at'])

    job = run.training_job
    _validate_training_job(job)
    get_or_create_document_knowledge_source(training_job=job)

    semantic_qs = semantic_embeddings_for_chunking_run(run.chunking_run)
    if not semantic_qs.exists():
        run.status = IndexingRunStatus.SKIPPED
        run.skip_reason = SKIP_REASON_SEMANTIC_UNAVAILABLE
        run.completed_at = datetime.now(timezone.utc)
        run.save(update_fields=['status', 'skip_reason', 'completed_at', 'updated_at'])
        _update_knowledge_sources(
            document_id=run.document_id,
            business_model_id=run.business_model_id,
            indexing_status=KnowledgeIndexingStatus.PENDING,
        )
        return

    _update_knowledge_sources(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
        indexing_status=KnowledgeIndexingStatus.PROCESSING,
    )

    gateway = get_qdrant_gateway()
    try:
        gateway.ensure_collection(collection_name=run.collection_name, dimension=run.embedding_dimension)
    except QdrantUnavailableError as exc:
        _mark_transient_failure(run, exc)
        raise
    except QdrantGatewayError as exc:
        _mark_run_failed(run, message=str(exc))
        raise IndexingServiceError(str(exc)) from exc

    batch_size = settings.QDRANT_UPSERT_BATCH_SIZE
    artifact_version = run.artifact_version

    embeddings = _load_semantic_embeddings(run.chunking_run)
    run.total_chunks = len(embeddings)
    run.save(update_fields=['total_chunks', 'updated_at'])

    already_indexed_ids = set(
        ChunkVectorIndex.objects.filter(
            indexing_run=run,
            status=ChunkVectorIndexStatus.INDEXED,
        ).values_list('chunk_embedding_id', flat=True)
    )

    for offset in range(0, len(embeddings), batch_size):
        batch = embeddings[offset : offset + batch_size]
        points: list[QdrantPoint] = []
        batch_embeddings: list = []
        for embedding in batch:
            if embedding.id in already_indexed_ids:
                continue
            chunk = embedding.document_chunk
            try:
                vector = _vector_from_embedding(embedding)
            except Exception as exc:
                ChunkVectorIndex.objects.update_or_create(
                    indexing_run=run,
                    chunk_embedding=embedding,
                    defaults={
                        'document_chunk': chunk,
                        'qdrant_point_id': chunk.id,
                        'collection_name': run.collection_name,
                        'embedding_dimension': run.embedding_dimension,
                        'status': ChunkVectorIndexStatus.FAILED,
                        'error_message': str(exc),
                    },
                )
                continue

            payload = build_point_payload(
                chunk=chunk,
                embedding=embedding,
                business_model_key=run.business_model.key,
                artifact_version=artifact_version,
                is_active=False,
            )
            points.append(
                QdrantPoint(point_id=str(chunk.id), vector=vector, payload=payload)
            )
            batch_embeddings.append(embedding)
            ChunkVectorIndex.objects.update_or_create(
                indexing_run=run,
                chunk_embedding=embedding,
                defaults={
                    'document_chunk': chunk,
                    'qdrant_point_id': chunk.id,
                    'collection_name': run.collection_name,
                    'embedding_dimension': run.embedding_dimension,
                    'status': ChunkVectorIndexStatus.PENDING,
                    'error_message': '',
                },
            )

        if not points:
            IndexingRun.objects.filter(pk=run.pk).update(updated_at=datetime.now(timezone.utc))
            continue
        try:
            gateway.upsert_points(collection_name=run.collection_name, points=points)
        except QdrantUnavailableError as exc:
            _mark_transient_failure(run, exc)
            raise
        except QdrantGatewayError as exc:
            _mark_run_failed(run, message=exc.args[0] if exc.args else 'Qdrant upsert failed.')
            raise IndexingServiceError(str(exc)) from exc

        now = datetime.now(timezone.utc)
        for embedding in batch_embeddings:
            ChunkVectorIndex.objects.filter(
                indexing_run=run,
                chunk_embedding=embedding,
            ).update(
                status=ChunkVectorIndexStatus.INDEXED,
                indexed_at=now,
                error_message='',
            )
        IndexingRun.objects.filter(pk=run.pk).update(updated_at=now)

    indexed = ChunkVectorIndex.objects.filter(
        indexing_run=run,
        status=ChunkVectorIndexStatus.INDEXED,
    ).count()
    failed = ChunkVectorIndex.objects.filter(
        indexing_run=run,
        status=ChunkVectorIndexStatus.FAILED,
    ).count()

    if failed or indexed != run.total_chunks:
        _mark_run_failed(
            run,
            message='Not all semantic embeddings were indexed successfully.',
            indexed=indexed,
            failed=failed,
        )
        raise IndexingServiceError(run.error_message)

    activation_before = DocumentIndexActivation.objects.filter(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
    ).first()
    previous_artifact = (
        activation_before.active_artifact_version if activation_before and activation_before.active_collection_name else None
    )
    previous_collection = activation_before.active_collection_name if activation_before else ''

    try:
        _record_pending_activation(run=run)
    except IndexingServiceError as exc:
        _mark_run_failed(run, message=exc.message)
        raise

    run.activation_phase = IndexingActivationPhase.PENDING_RECORDED
    run.save(update_fields=['activation_phase', 'updated_at'])

    try:
        run.activation_phase = IndexingActivationPhase.QDRANT_ACTIVATING
        run.save(update_fields=['activation_phase', 'updated_at'])

        _activate_qdrant_for_run(
            gateway=gateway,
            run=run,
            embeddings=embeddings,
            previous_artifact=previous_artifact,
            previous_collection=previous_collection,
            batch_size=batch_size,
        )

        run.activation_phase = IndexingActivationPhase.QDRANT_ACTIVATED
        run.activation_reconciled = False
        run.save(update_fields=['activation_phase', 'activation_reconciled', 'updated_at'])

        with transaction.atomic():
            activation = DocumentIndexActivation.objects.select_for_update().get(
                document_id=run.document_id,
                business_model_id=run.business_model_id,
            )
            _commit_activation_from_pending(activation=activation, run=run)

    except QdrantUnavailableError as exc:
        _mark_transient_failure(run, exc)
        raise
    except QdrantGatewayError as exc:
        run.activation_reconciled = False
        run.save(update_fields=['activation_reconciled', 'updated_at'])
        _mark_run_failed(
            run,
            message=f'Qdrant activation failed; PostgreSQL active version preserved: {exc}',
            indexed=indexed,
            failed=failed,
            clear_pending=False,
        )
        raise IndexingServiceError(run.error_message) from exc

    run.status = IndexingRunStatus.COMPLETED
    run.indexed_chunks = indexed
    run.failed_chunks = failed
    run.completed_at = datetime.now(timezone.utc)
    run.activation_phase = IndexingActivationPhase.COMMITTED
    run.activation_reconciled = True
    run.save(
        update_fields=[
            'status',
            'indexed_chunks',
            'failed_chunks',
            'completed_at',
            'activation_phase',
            'activation_reconciled',
            'updated_at',
        ]
    )
    _update_knowledge_sources(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
        indexing_status=KnowledgeIndexingStatus.INDEXED,
        vector_store=run.collection_name,
    )
    logger.info(
        'indexing_run_completed run_id=%s document_id=%s collection=%s points=%s',
        run.id,
        run.document_id,
        run.collection_name,
        indexed,
    )
