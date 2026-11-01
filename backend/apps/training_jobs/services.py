"""
Training job business logic (model-agnostic, future Celery-ready).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.documents.access import documents_for_user
from apps.documents.models import Document
from apps.model_management.models import BusinessModel
from apps.training_jobs.document_sync import (
    is_document_eligible_for_new_job,
    sync_document_for_job_status,
)
from apps.training_jobs.lifecycle import (
    InvalidJobTransitionError,
    validate_progress_for_status,
    validate_transition,
)
from apps.training_jobs.dispatch import schedule_training_job_dispatch
from apps.training_jobs.models import TrainingJob, TrainingJobStatus

DEFAULT_MAX_RETRIES = 3
TRAINING_JOB_MAX_RETRIES = int(os.environ.get('TRAINING_JOB_MAX_RETRIES', str(DEFAULT_MAX_RETRIES)))


class TrainingJobServiceError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _get_owned_documents(user, document_ids: list, business_model: BusinessModel) -> list[Document]:
    unique_ids = list(dict.fromkeys(document_ids))
    documents = list(
        documents_for_user(user).filter(
            id__in=unique_ids,
            business_model=business_model,
        )
    )
    found_ids = {str(doc.id) for doc in documents}
    missing = [str(doc_id) for doc_id in unique_ids if str(doc_id) not in found_ids]
    if missing:
        raise TrainingJobServiceError(
            'One or more documents were not found for this user and business model.'
        )
    return documents


@transaction.atomic
def create_training_jobs(
    *,
    user,
    business_model: BusinessModel,
    document_ids: list,
) -> list[TrainingJob]:
    if not document_ids:
        raise ValidationError({'document_ids': 'At least one document id is required.'})

    documents = _get_owned_documents(user, document_ids, business_model)
    ineligible = [str(doc.id) for doc in documents if not is_document_eligible_for_new_job(doc)]
    if ineligible:
        raise ValidationError(
            {
                'document_ids': (
                    'One or more documents are not eligible for training '
                    f'(inactive job or unsupported status): {", ".join(ineligible)}'
                ),
            }
        )

    created: list[TrainingJob] = []
    for document in documents:
        job = TrainingJob(
            user=user,
            business_model=business_model,
            document=document,
            status=TrainingJobStatus.QUEUED,
            progress=0,
            current_stage='queued',
            retry_count=0,
        )
        job.full_clean()
        job.save()
        created.append(job)
        schedule_training_job_dispatch(str(job.id))
    return created


@transaction.atomic
def transition_training_job(
    job: TrainingJob,
    *,
    new_status: str,
    progress: int | None = None,
    current_stage: str | None = None,
    error_message: str | None = None,
) -> TrainingJob:
    validate_transition(job.status, new_status)

    next_progress = job.progress if progress is None else progress
    validate_progress_for_status(status=new_status, progress=next_progress)

    job.status = new_status
    job.progress = next_progress

    if current_stage is not None:
        job.current_stage = current_stage

    if new_status == TrainingJobStatus.PROCESSING and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)

    if new_status in {
        TrainingJobStatus.COMPLETED,
        TrainingJobStatus.FAILED,
        TrainingJobStatus.CANCELLED,
    }:
        job.completed_at = datetime.now(timezone.utc)

    if new_status == TrainingJobStatus.FAILED:
        job.error_message = (error_message or 'Training job failed.').strip()
    elif new_status == TrainingJobStatus.COMPLETED:
        job.error_message = ''

    job.full_clean()
    job.save()
    sync_document_for_job_status(job)
    return job


@transaction.atomic
def retry_training_job(job: TrainingJob, *, user) -> TrainingJob:
    if job.user_id != user.pk:
        raise TrainingJobServiceError('Job not found.')

    if job.status != TrainingJobStatus.FAILED:
        raise TrainingJobServiceError('Only failed jobs can be retried.')

    if job.retry_count >= TRAINING_JOB_MAX_RETRIES:
        raise TrainingJobServiceError(
            f'Maximum retry count ({TRAINING_JOB_MAX_RETRIES}) reached for this job lineage.'
        )

    document = job.document
    if not is_document_eligible_for_new_job(document):
        raise TrainingJobServiceError('Document is not eligible for a retry job.')

    new_job = TrainingJob(
        user=user,
        business_model=job.business_model,
        document=document,
        parent_job=job,
        status=TrainingJobStatus.QUEUED,
        progress=0,
        current_stage='queued',
        retry_count=job.retry_count + 1,
    )
    new_job.full_clean()
    new_job.save()
    schedule_training_job_dispatch(str(new_job.id))
    return new_job


@transaction.atomic
def cancel_training_job(job: TrainingJob, *, user) -> TrainingJob:
    if job.user_id != user.pk:
        raise TrainingJobServiceError('Job not found.')

    if job.status == TrainingJobStatus.PROCESSING:
        raise TrainingJobServiceError(
            'Processing jobs cannot be cancelled until worker cancellation is implemented.'
        )

    if job.status == TrainingJobStatus.RETRYING:
        raise TrainingJobServiceError(
            'Retrying jobs cannot be cancelled until worker cancellation is implemented.'
        )

    if job.status != TrainingJobStatus.QUEUED:
        raise TrainingJobServiceError(
            f'Jobs in status "{job.status}" cannot be cancelled.'
        )

    return transition_training_job(
        job,
        new_status=TrainingJobStatus.CANCELLED,
        progress=job.progress,
        current_stage='cancelled',
    )
