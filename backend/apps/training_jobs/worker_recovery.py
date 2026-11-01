"""
Recover queued jobs after broker outages and stale ``processing`` rows after worker loss.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.db import transaction

from apps.training_jobs.dispatch import dispatch_training_job_now, schedule_training_job_dispatch
from apps.training_jobs.models import TrainingJob, TrainingJobStatus
from apps.training_jobs.services import transition_training_job


def stale_processing_cutoff() -> datetime:
    seconds = settings.TRAINING_JOB_STALE_PROCESSING_SECONDS
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def recover_stale_processing_jobs() -> list[str]:
    """
    Mark long-running ``processing`` jobs as failed so they can be retried explicitly.

    Does not auto-dispatch; operators or users retry through the API.
    """
    cutoff = stale_processing_cutoff()
    stale_ids: list[str] = []
    stale_jobs = TrainingJob.objects.filter(
        status=TrainingJobStatus.PROCESSING,
        updated_at__lt=cutoff,
    ).order_by('updated_at')

    for job in stale_jobs:
        with transaction.atomic():
            locked = (
                TrainingJob.objects.select_for_update()
                .filter(pk=job.pk, status=TrainingJobStatus.PROCESSING)
                .first()
            )
            if locked is None:
                continue
            if locked.updated_at >= cutoff:
                continue
            transition_training_job(
                locked,
                new_status=TrainingJobStatus.FAILED,
                progress=locked.progress,
                current_stage='worker_interrupted',
                error_message=(
                    'Processing interrupted (worker shutdown or timeout). '
                    'Retry the job when workers are healthy.'
                ),
            )
            stale_ids.append(str(locked.pk))
    return stale_ids


def redispatch_queued_jobs(*, only_dispatch_errors: bool = True) -> list[str]:
    """
    Re-enqueue ``queued`` jobs (typically after Redis recovers).

    When ``only_dispatch_errors`` is True, only jobs with a recorded ``dispatch_error``
    are re-dispatched.
    """
    qs = TrainingJob.objects.filter(status=TrainingJobStatus.QUEUED).order_by('created_at')
    if only_dispatch_errors:
        qs = qs.exclude(dispatch_error='')

    redispatched: list[str] = []
    for job in qs:
        job_id = str(job.pk)
        try:
            dispatch_training_job_now(job_id)
        except Exception:
            continue
        redispatched.append(job_id)
    return redispatched


def schedule_redispatch_queued_jobs(*, only_dispatch_errors: bool = True) -> None:
    qs = TrainingJob.objects.filter(status=TrainingJobStatus.QUEUED).order_by('created_at')
    if only_dispatch_errors:
        qs = qs.exclude(dispatch_error='')
    for job in qs:
        schedule_training_job_dispatch(str(job.pk))
