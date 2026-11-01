"""
Enqueue TrainingJob Celery tasks after PostgreSQL commits.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction

from apps.training_jobs.models import TrainingJob

logger = logging.getLogger(__name__)

DISPATCH_ERROR_MAX_LENGTH = 2000


def _safe_dispatch_error(exc: BaseException) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if len(message) > DISPATCH_ERROR_MAX_LENGTH:
        return message[: DISPATCH_ERROR_MAX_LENGTH - 3] + '...'
    return message


def send_training_job_task(job_id: str) -> None:
    """
    Publish ``process_training_job`` to the broker.

    Raises on broker/publish failures so callers can record ``dispatch_error``.
    """
    from apps.training_jobs.tasks import process_training_job

    process_training_job.delay(str(job_id))


def record_dispatch_success(job_id: str) -> None:
    TrainingJob.objects.filter(pk=job_id).update(
        dispatch_error='',
        last_dispatched_at=datetime.now(timezone.utc),
    )


def record_dispatch_failure(job_id: str, exc: BaseException) -> None:
    error = _safe_dispatch_error(exc)
    TrainingJob.objects.filter(pk=job_id).update(dispatch_error=error)
    logger.warning(
        'training_job_dispatch_failed job_id=%s error=%s',
        job_id,
        error,
    )


def dispatch_training_job_now(job_id: str) -> None:
    """Dispatch immediately (used by recovery and post-commit hooks)."""
    if settings.CELERY_TASK_ALWAYS_EAGER:
        send_training_job_task(job_id)
        record_dispatch_success(job_id)
        return

    try:
        send_training_job_task(job_id)
    except Exception as exc:
        record_dispatch_failure(job_id, exc)
        raise
    record_dispatch_success(job_id)


def schedule_training_job_dispatch(job_id: str) -> None:
    """Schedule broker dispatch after the surrounding DB transaction commits."""

    def _on_commit() -> None:
        try:
            dispatch_training_job_now(job_id)
        except Exception:
            # Failure is persisted on the job row; do not raise after commit.
            pass

    transaction.on_commit(_on_commit)
