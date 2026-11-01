from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction

from apps.knowledge.models import KnowledgeIndexingStatus
from apps.vector_indexing.constants import (
    ERROR_REQUIRES_RECONCILIATION,
    ChunkVectorIndexStatus,
    IndexingActivationPhase,
    IndexingRunStatus,
)
from apps.vector_indexing.models import ChunkVectorIndex, DocumentIndexActivation, IndexingRun
from apps.vector_indexing.services import (
    IndexingServiceError,
    _activate_qdrant_for_run,
    _build_points_for_embeddings,
    _commit_activation_from_pending,
    _load_semantic_embeddings,
    _resolve_knowledge_indexing_status,
    _update_knowledge_sources,
    _vector_from_embedding,
)
from gateways.qdrant.exceptions import QdrantGatewayError
from gateways.qdrant.factory import get_qdrant_gateway

logger = logging.getLogger(__name__)


def list_reconciliation_candidates() -> list[str]:
    pending_run_ids = DocumentIndexActivation.objects.filter(
        pending_indexing_run__isnull=False,
    ).values_list('pending_indexing_run_id', flat=True)
    inconsistent = IndexingRun.objects.filter(
        status=IndexingRunStatus.FAILED,
        activation_reconciled=False,
        indexed_chunks__gt=0,
    ).values_list('id', flat=True)
    qdrant_ahead = IndexingRun.objects.filter(
        activation_phase=IndexingActivationPhase.QDRANT_ACTIVATED,
    ).values_list('id', flat=True)
    return list(set(map(str, pending_run_ids)) | set(map(str, inconsistent)) | set(map(str, qdrant_ahead)))


def _sync_qdrant_active_flags_from_pg(*, activation: DocumentIndexActivation) -> None:
    """Idempotently align Qdrant is_active flags with PostgreSQL activation row."""
    gateway = get_qdrant_gateway()
    document_id = str(activation.document_id)
    active_collection = activation.active_collection_name
    active_artifact = activation.active_artifact_version

    if active_collection:
        gateway.set_payload_by_filter(
            collection_name=active_collection,
            payload={'is_active': True},
            document_id=document_id,
            artifact_version=active_artifact,
        )

    pending = activation.pending_indexing_run
    if pending and pending.collection_name and pending.collection_name != active_collection:
        if pending.artifact_version != active_artifact:
            gateway.set_payload_by_filter(
                collection_name=pending.collection_name,
                payload={'is_active': False},
                document_id=document_id,
                artifact_version=pending.artifact_version,
            )


def reconcile_indexing_run(run_id: str) -> None:
    """
    Repair Qdrant payload activation using PostgreSQL DocumentIndexActivation as authority.

    Safe to call repeatedly. Does not delete historical vectors.
    """
    run = (
        IndexingRun.objects.select_related(
            'document',
            'business_model',
            'chunking_run',
        )
        .filter(pk=run_id)
        .first()
    )
    if run is None:
        raise IndexingServiceError(f'Indexing run not found: {run_id}')

    if run.status == IndexingRunStatus.SKIPPED:
        return

    gateway = get_qdrant_gateway()
    batch_size = settings.QDRANT_UPSERT_BATCH_SIZE

    with transaction.atomic():
        activation = (
            DocumentIndexActivation.objects.select_for_update()
            .filter(
                document_id=run.document_id,
                business_model_id=run.business_model_id,
            )
            .first()
        )

    if activation is None:
        if run.status != IndexingRunStatus.COMPLETED:
            raise IndexingServiceError(
                'No DocumentIndexActivation row; run cannot be reconciled until indexing completes.'
            )
        return

    pending_run = activation.pending_indexing_run
    if pending_run is not None and str(pending_run.pk) != str(run.pk):
        raise IndexingServiceError(
            'Another indexing run is pending activation for this document; reconcile that run first.'
        )

    indexed_qs = ChunkVectorIndex.objects.filter(
        indexing_run=run,
        status=ChunkVectorIndexStatus.INDEXED,
    ).select_related('chunk_embedding__document_chunk')

    if pending_run is not None and str(pending_run.pk) == str(run.pk):
        embeddings = _load_semantic_embeddings(run.chunking_run)
        indexed_ids = set(indexed_qs.values_list('chunk_embedding_id', flat=True))
        if len(indexed_ids) != len(embeddings):
            for offset in range(0, len(embeddings), batch_size):
                batch = embeddings[offset : offset + batch_size]
                points = []
                for embedding in batch:
                    if embedding.id in indexed_ids:
                        continue
                    chunk = embedding.document_chunk
                    vector = _vector_from_embedding(embedding)
                    points.extend(
                        _build_points_for_embeddings(
                            run=run,
                            embeddings=[embedding],
                            vectors=[vector],
                            is_active=False,
                        )
                    )
                if points:
                    gateway.upsert_points(collection_name=run.collection_name, points=points)
                    now = datetime.now(timezone.utc)
                    for embedding in batch:
                        if embedding.id in indexed_ids:
                            continue
                        ChunkVectorIndex.objects.update_or_create(
                            indexing_run=run,
                            chunk_embedding=embedding,
                            defaults={
                                'document_chunk': embedding.document_chunk,
                                'qdrant_point_id': embedding.document_chunk_id,
                                'collection_name': run.collection_name,
                                'embedding_dimension': run.embedding_dimension,
                                'status': ChunkVectorIndexStatus.INDEXED,
                                'indexed_at': now,
                                'error_message': '',
                            },
                        )

        previous_artifact = None
        previous_collection = ''
        if (
            activation.active_collection_name
            and activation.active_indexing_run_id
            and activation.active_artifact_version != run.artifact_version
        ):
            previous_artifact = activation.active_artifact_version
            previous_collection = activation.active_collection_name

        _activate_qdrant_for_run(
            gateway=gateway,
            run=run,
            embeddings=embeddings,
            previous_artifact=previous_artifact if previous_artifact != run.artifact_version else None,
            previous_collection=previous_collection,
            batch_size=batch_size,
        )

        with transaction.atomic():
            activation = DocumentIndexActivation.objects.select_for_update().get(pk=activation.pk)
            if activation.pending_indexing_run_id != run.pk:
                raise IndexingServiceError('Pending activation changed during reconciliation.')
            _commit_activation_from_pending(activation=activation, run=run)

        run.refresh_from_db()
        run.status = IndexingRunStatus.COMPLETED
        run.activation_phase = IndexingActivationPhase.COMMITTED
        run.activation_reconciled = True
        run.error_message = ''
        run.completed_at = datetime.now(timezone.utc)
        run.save(
            update_fields=[
                'status',
                'activation_phase',
                'activation_reconciled',
                'error_message',
                'completed_at',
                'updated_at',
            ]
        )
        _update_knowledge_sources(
            document_id=run.document_id,
            business_model_id=run.business_model_id,
            indexing_status=KnowledgeIndexingStatus.INDEXED,
            vector_store=run.collection_name,
        )
        logger.info('indexing_run_reconciled run_id=%s', run.id)
        return

    if run.activation_phase == IndexingActivationPhase.QDRANT_ACTIVATED:
        with transaction.atomic():
            activation = DocumentIndexActivation.objects.select_for_update().get(pk=activation.pk)
            _commit_activation_from_pending(activation=activation, run=run)
        run.refresh_from_db()
        run.status = IndexingRunStatus.COMPLETED
        run.activation_phase = IndexingActivationPhase.COMMITTED
        run.activation_reconciled = True
        run.error_message = ''
        run.completed_at = datetime.now(timezone.utc)
        run.save(
            update_fields=[
                'status',
                'activation_phase',
                'activation_reconciled',
                'error_message',
                'completed_at',
                'updated_at',
            ]
        )
        _update_knowledge_sources(
            document_id=run.document_id,
            business_model_id=run.business_model_id,
            indexing_status=KnowledgeIndexingStatus.INDEXED,
            vector_store=run.collection_name,
        )
        return

    try:
        _sync_qdrant_active_flags_from_pg(activation=activation)
    except QdrantGatewayError as exc:
        raise IndexingServiceError(
            f'Qdrant reconciliation failed: {exc}'
        ) from exc

    if run.status == IndexingRunStatus.FAILED and run.error_message.startswith(
        'PostgreSQL activation succeeded'
    ):
        run.error_message = ERROR_REQUIRES_RECONCILIATION
        run.save(update_fields=['error_message', 'updated_at'])

    ks_status = _resolve_knowledge_indexing_status(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
    )
    _update_knowledge_sources(
        document_id=run.document_id,
        business_model_id=run.business_model_id,
        indexing_status=ks_status,
        vector_store=activation.active_collection_name,
    )
