from __future__ import annotations

from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import transaction

from apps.knowledge.models import KnowledgeIndexingStatus
from apps.vector_indexing.constants import ERROR_INDEXING_INTERRUPTED, IndexingRunStatus
from apps.vector_indexing.dispatch import dispatch_indexing_run_now
from apps.vector_indexing.models import DocumentIndexActivation, IndexingRun
from apps.vector_indexing.services import _clear_pending_activation, _update_knowledge_sources


def stale_indexing_cutoff() -> datetime:
    seconds = settings.INDEXING_RUN_STALE_PROCESSING_SECONDS
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def _knowledge_status_after_stale_failure(*, document_id, business_model_id) -> str:
    activation = DocumentIndexActivation.objects.filter(
        document_id=document_id,
        business_model_id=business_model_id,
    ).first()
    if activation and activation.active_collection_name:
        return KnowledgeIndexingStatus.INDEXED
    return KnowledgeIndexingStatus.FAILED


def recover_stale_indexing_runs() -> list[str]:
    cutoff = stale_indexing_cutoff()
    recovered: list[str] = []
    stale = IndexingRun.objects.filter(
        status=IndexingRunStatus.PROCESSING,
        updated_at__lt=cutoff,
    ).order_by('updated_at')

    for run in stale:
        with transaction.atomic():
            locked = (
                IndexingRun.objects.select_for_update()
                .filter(pk=run.pk, status=IndexingRunStatus.PROCESSING)
                .first()
            )
            if locked is None or locked.updated_at >= cutoff:
                continue
            locked.status = IndexingRunStatus.FAILED
            locked.error_message = ERROR_INDEXING_INTERRUPTED
            locked.completed_at = datetime.now(timezone.utc)
            locked.save(
                update_fields=['status', 'error_message', 'completed_at', 'updated_at']
            )
            _clear_pending_activation(
                document_id=locked.document_id,
                business_model_id=locked.business_model_id,
                run_id=locked.pk,
            )
            ks_status = _knowledge_status_after_stale_failure(
                document_id=locked.document_id,
                business_model_id=locked.business_model_id,
            )
            activation = DocumentIndexActivation.objects.filter(
                document_id=locked.document_id,
                business_model_id=locked.business_model_id,
            ).first()
            vector_store = activation.active_collection_name if activation else ''
            _update_knowledge_sources(
                document_id=locked.document_id,
                business_model_id=locked.business_model_id,
                indexing_status=ks_status,
                vector_store=vector_store,
            )
            recovered.append(str(locked.pk))
    return recovered


def redispatch_queued_indexing_runs(*, only_dispatch_errors: bool = True) -> list[str]:
    qs = IndexingRun.objects.filter(status=IndexingRunStatus.QUEUED).order_by('created_at')
    if only_dispatch_errors:
        qs = qs.exclude(dispatch_error='')
    redispatched: list[str] = []
    for run in qs:
        try:
            dispatch_indexing_run_now(str(run.pk))
        except Exception:
            continue
        redispatched.append(str(run.pk))
    return redispatched


def list_reconciliation_candidates() -> list[str]:
    from apps.vector_indexing.reconciliation import list_reconciliation_candidates as _list

    return _list()
