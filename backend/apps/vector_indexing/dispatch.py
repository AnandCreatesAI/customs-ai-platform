from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction

from apps.training_jobs.dispatch import DISPATCH_ERROR_MAX_LENGTH, _safe_dispatch_error
from apps.training_jobs.models import TrainingJob, TrainingJobStatus
from apps.vector_indexing.constants import IndexingRunStatus
from apps.vector_indexing.models import IndexingRun
from apps.vector_indexing.services import prepare_indexing_run

logger = logging.getLogger(__name__)


def send_indexing_task(indexing_run_id: str) -> None:
    from apps.vector_indexing.tasks import process_indexing_run

    process_indexing_run.delay(str(indexing_run_id))


def record_indexing_dispatch_success(indexing_run_id: str) -> None:
    IndexingRun.objects.filter(pk=indexing_run_id).update(dispatch_error='')


def record_indexing_dispatch_failure(indexing_run_id: str, exc: BaseException) -> None:
    error = _safe_dispatch_error(exc)
    IndexingRun.objects.filter(pk=indexing_run_id).update(dispatch_error=error)
    logger.warning(
        'indexing_run_dispatch_failed run_id=%s error=%s',
        indexing_run_id,
        error[:DISPATCH_ERROR_MAX_LENGTH],
    )


def dispatch_indexing_run_now(indexing_run_id: str) -> None:
    if settings.CELERY_TASK_ALWAYS_EAGER:
        send_indexing_task(indexing_run_id)
        record_indexing_dispatch_success(indexing_run_id)
        return
    try:
        send_indexing_task(indexing_run_id)
    except Exception as exc:
        record_indexing_dispatch_failure(indexing_run_id, exc)
        raise
    record_indexing_dispatch_success(indexing_run_id)


def schedule_indexing_for_training_job(training_job_id: str) -> None:
    if not settings.QDRANT_INDEXING_ENABLED:
        return

    def _on_commit() -> None:
        job = TrainingJob.objects.select_related('document', 'business_model').filter(
            pk=training_job_id,
            status=TrainingJobStatus.COMPLETED,
        ).first()
        if job is None:
            return
        try:
            run = prepare_indexing_run(training_job=job)
        except Exception as exc:
            logger.warning(
                'indexing_prepare_failed job_id=%s error=%s',
                training_job_id,
                _safe_dispatch_error(exc),
            )
            return
        if run.status == IndexingRunStatus.SKIPPED:
            logger.info(
                'indexing_skipped job_id=%s run_id=%s reason=%s',
                training_job_id,
                run.id,
                run.skip_reason,
            )
            return
        try:
            dispatch_indexing_run_now(str(run.id))
        except Exception:
            pass

    transaction.on_commit(_on_commit)
