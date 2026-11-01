"""
Celery tasks for TrainingJob execution (model-agnostic).
"""

from __future__ import annotations

import logging

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import close_old_connections, transaction
from kombu.exceptions import OperationalError

from apps.training_jobs.lifecycle import TERMINAL_STATUSES
from apps.training_jobs.models import TrainingJob, TrainingJobStatus
from apps.document_extraction.services.run_extraction import ExtractionFailedError
from apps.document_chunking.exceptions import ChunkingFailedError, EmbeddingFailedError
from apps.training_jobs.processing import get_training_job_processor
from apps.training_jobs.document_sync import sync_document_for_job_status
from apps.training_jobs.services import transition_training_job
from apps.training_jobs.worker_recovery import stale_processing_cutoff

logger = logging.getLogger(__name__)

TASK_NAME = 'training_jobs.process_training_job'


class JobExecutionOutcome:
    SKIPPED = 'skipped'
    STARTED = 'started'
    FAILED = 'failed'
    DUPLICATE = 'duplicate'


def _fail_corrupt_job(job: TrainingJob, *, error_message: str, current_stage: str) -> None:
    """Persist failure for inconsistent rows without lifecycle transitions."""
    from datetime import datetime, timezone

    job.status = TrainingJobStatus.FAILED
    job.error_message = error_message
    job.current_stage = current_stage
    job.completed_at = datetime.now(timezone.utc)
    job.save(
        update_fields=[
            'status',
            'error_message',
            'current_stage',
            'completed_at',
            'updated_at',
        ]
    )
    sync_document_for_job_status(job)


def _validate_job_relationships(job: TrainingJob) -> bool:
    document = job.document
    if document.user_id != job.user_id:
        logger.warning('training_job_skipped job_id=%s reason=document_user_mismatch', job.id)
        return False
    if document.business_model_id != job.business_model_id:
        logger.warning(
            'training_job_skipped job_id=%s reason=document_business_model_mismatch',
            job.id,
        )
        return False
    return True


def _is_stale_processing(job: TrainingJob) -> bool:
    if job.status != TrainingJobStatus.PROCESSING:
        return False
    return job.updated_at < stale_processing_cutoff()


def run_process_training_job(job_id: str) -> str:
    """
    Core task body (testable without Celery).

    PostgreSQL row locking prevents concurrent duplicate execution.
    """

    with transaction.atomic():
        job = (
            TrainingJob.objects.select_for_update()
            .select_related('document', 'business_model', 'user')
            .filter(pk=job_id)
            .first()
        )
        if job is None:
            logger.info('training_job_missing job_id=%s', job_id)
            return JobExecutionOutcome.SKIPPED

        if job.status in TERMINAL_STATUSES:
            logger.info(
                'training_job_terminal_skip job_id=%s status=%s',
                job_id,
                job.status,
            )
            return JobExecutionOutcome.SKIPPED

        if job.status == TrainingJobStatus.PROCESSING:
            if _is_stale_processing(job):
                transition_training_job(
                    job,
                    new_status=TrainingJobStatus.FAILED,
                    progress=job.progress,
                    current_stage='worker_interrupted',
                    error_message=(
                        'Processing interrupted (stale worker task). '
                        'Retry the job when workers are healthy.'
                    ),
                )
                return JobExecutionOutcome.FAILED
            logger.info('training_job_duplicate_skip job_id=%s status=processing', job_id)
            return JobExecutionOutcome.DUPLICATE

        if job.status != TrainingJobStatus.QUEUED:
            logger.info(
                'training_job_unexpected_status job_id=%s status=%s',
                job_id,
                job.status,
            )
            return JobExecutionOutcome.SKIPPED

        if not _validate_job_relationships(job):
            _fail_corrupt_job(
                job,
                error_message='Job failed ownership validation.',
                current_stage='validation_failed',
            )
            return JobExecutionOutcome.FAILED

        transition_training_job(
            job,
            new_status=TrainingJobStatus.PROCESSING,
            progress=0,
            current_stage='processing',
        )

    job = TrainingJob.objects.select_related('document', 'business_model').get(pk=job_id)
    if job.status != TrainingJobStatus.PROCESSING:
        return JobExecutionOutcome.SKIPPED

    processor = get_training_job_processor()
    try:
        processor.run(job)
        job.refresh_from_db()
        if job.status in TERMINAL_STATUSES:
            return JobExecutionOutcome.SKIPPED
        transition_training_job(
            job,
            new_status=TrainingJobStatus.COMPLETED,
            progress=100,
            current_stage='completed',
        )
        from apps.vector_indexing.dispatch import schedule_indexing_for_training_job

        schedule_indexing_for_training_job(str(job.id))
        return JobExecutionOutcome.STARTED
    except ExtractionFailedError as exc:
        job.refresh_from_db()
        if job.status in TERMINAL_STATUSES:
            return JobExecutionOutcome.SKIPPED
        transition_training_job(
            job,
            new_status=TrainingJobStatus.FAILED,
            progress=job.progress,
            current_stage='extraction_failed',
            error_message=exc.message,
        )
        return JobExecutionOutcome.FAILED
    except ChunkingFailedError as exc:
        job.refresh_from_db()
        if job.status in TERMINAL_STATUSES:
            return JobExecutionOutcome.SKIPPED
        transition_training_job(
            job,
            new_status=TrainingJobStatus.FAILED,
            progress=job.progress,
            current_stage='chunking_failed',
            error_message=exc.message,
        )
        return JobExecutionOutcome.FAILED
    except EmbeddingFailedError as exc:
        job.refresh_from_db()
        if job.status in TERMINAL_STATUSES:
            return JobExecutionOutcome.SKIPPED
        transition_training_job(
            job,
            new_status=TrainingJobStatus.FAILED,
            progress=job.progress,
            current_stage='embedding_failed',
            error_message=exc.message,
        )
        return JobExecutionOutcome.FAILED
    except SoftTimeLimitExceeded:
        job.refresh_from_db()
        if job.status not in TERMINAL_STATUSES:
            transition_training_job(
                job,
                new_status=TrainingJobStatus.FAILED,
                progress=job.progress,
                current_stage='soft_time_limit',
                error_message='Training job exceeded the soft time limit.',
            )
        return JobExecutionOutcome.FAILED
    except Exception:
        logger.exception('training_job_unhandled_error job_id=%s', job_id)
        job.refresh_from_db()
        if job.status not in TERMINAL_STATUSES:
            transition_training_job(
                job,
                new_status=TrainingJobStatus.FAILED,
                progress=job.progress,
                current_stage='processing_error',
                error_message='Training job failed due to an unexpected error.',
            )
        return JobExecutionOutcome.FAILED


@shared_task(
    bind=True,
    name=TASK_NAME,
    acks_late=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=settings.TRAINING_JOB_CELERY_MAX_RETRIES,
)
def process_training_job(self, job_id: str) -> str:
    close_old_connections()
    logger.info(
        'training_job_task_received job_id=%s task_id=%s',
        job_id,
        self.request.id,
    )
    try:
        return run_process_training_job(str(job_id))
    finally:
        close_old_connections()
