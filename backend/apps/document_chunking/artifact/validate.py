from __future__ import annotations

from django.conf import settings

from apps.document_extraction.models import ExtractionRun, ExtractionRunStatus
from apps.document_extraction.schema.types import ExtractionBundle
from apps.document_chunking.exceptions import ChunkingFailedError
from apps.training_jobs.models import TrainingJob


def validate_extraction_run_for_chunking(
    *,
    job: TrainingJob,
    run: ExtractionRun,
    bundle: ExtractionBundle,
) -> None:
    if run.status != ExtractionRunStatus.SUCCEEDED:
        raise ChunkingFailedError('Extraction run did not succeed.')

    if run.training_job_id != job.id:
        raise ChunkingFailedError('Extraction run does not belong to this training job.')

    if run.document_id != job.document_id:
        raise ChunkingFailedError('Extraction run document mismatch.')

    if run.user_id != job.user_id:
        raise ChunkingFailedError('Extraction run user mismatch.')

    if run.business_model_id != job.business_model_id:
        raise ChunkingFailedError('Extraction run business model mismatch.')

    if str(run.document_id) != bundle.document_id:
        raise ChunkingFailedError('Artifact document_id does not match extraction run.')

    if bundle.business_model_key != job.business_model.key:
        raise ChunkingFailedError('Artifact business model key mismatch.')

    if str(job.id) != bundle.training_job_id:
        raise ChunkingFailedError('Artifact training_job_id mismatch.')

    if str(run.id) != bundle.extraction_run_id:
        raise ChunkingFailedError('Artifact extraction_run_id mismatch.')

    if len(bundle.elements) > settings.EXTRACTION_MAX_ELEMENTS:
        raise ChunkingFailedError('Extraction artifact exceeds configured element limit.')
