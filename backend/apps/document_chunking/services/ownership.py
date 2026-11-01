from __future__ import annotations

from django.core.exceptions import ValidationError

from apps.document_chunking.models import ChunkEmbedding, DocumentChunk
from apps.document_extraction.models import ExtractionRun
from apps.training_jobs.models import TrainingJob


def validate_training_job_document_alignment(job: TrainingJob) -> None:
    document = job.document
    if document.user_id != job.user_id:
        raise ValidationError('Job user must match document owner.')
    if document.business_model_id != job.business_model_id:
        raise ValidationError('Job business model must match document business model.')


def validate_chunk_row(*, chunk: DocumentChunk) -> None:
    if chunk.document.user_id != chunk.user_id:
        raise ValidationError('Chunk user must match document owner.')
    if chunk.document.business_model_id != chunk.business_model_id:
        raise ValidationError('Chunk business model must match document business model.')
    if chunk.extraction_run.document_id != chunk.document_id:
        raise ValidationError('Chunk extraction run document mismatch.')


def validate_embedding_row(*, embedding: ChunkEmbedding) -> None:
    validate_chunk_row(chunk=embedding.document_chunk)
