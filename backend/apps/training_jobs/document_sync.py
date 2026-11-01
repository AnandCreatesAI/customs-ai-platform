"""
Document status rules synchronized with TrainingJob lifecycle.

Job creation (queued) never marks a document processed. Workers in later phases will
drive processing/completed/failed transitions through this module.
"""

from __future__ import annotations

from apps.documents.models import Document, DocumentStatus
from apps.training_jobs.lifecycle import ACTIVE_STATUSES
from apps.training_jobs.models import TrainingJob, TrainingJobStatus


def document_has_active_job(document: Document, *, exclude_job_id=None) -> bool:
    qs = TrainingJob.objects.filter(
        document=document,
        status__in=ACTIVE_STATUSES,
    )
    if exclude_job_id:
        qs = qs.exclude(id=exclude_job_id)
    return qs.exists()


def is_document_eligible_for_new_job(document: Document) -> bool:
    if document.status == DocumentStatus.ARCHIVED:
        return False
    if document.status == DocumentStatus.PROCESSED:
        return False
    if document_has_active_job(document):
        return False
    return document.status in {
        DocumentStatus.UPLOADED,
        DocumentStatus.FAILED,
    }


def sync_document_for_job_status(job: TrainingJob) -> None:
    document = job.document
    status = job.status

    if status == TrainingJobStatus.QUEUED:
        return

    if status == TrainingJobStatus.PROCESSING:
        if document.status != DocumentStatus.PROCESSED:
            document.status = DocumentStatus.PROCESSING
            document.save(update_fields=['status', 'updated_at'])
        return

    if status == TrainingJobStatus.COMPLETED:
        document.status = DocumentStatus.PROCESSED
        document.save(update_fields=['status', 'updated_at'])
        return

    if status == TrainingJobStatus.FAILED:
        if not document_has_active_job(document, exclude_job_id=job.id):
            document.status = DocumentStatus.FAILED
            document.save(update_fields=['status', 'updated_at'])
        return

    if status == TrainingJobStatus.CANCELLED:
        if not document_has_active_job(document, exclude_job_id=job.id):
            if document.status == DocumentStatus.PROCESSING:
                document.status = DocumentStatus.UPLOADED
                document.save(update_fields=['status', 'updated_at'])
        return
