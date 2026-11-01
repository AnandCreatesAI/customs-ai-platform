from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone

from django.db import transaction

from apps.document_chunking.artifact.reader import load_bundle_for_run
from apps.document_chunking.artifact.validate import validate_extraction_run_for_chunking
from apps.document_chunking.config import get_chunking_config
from apps.document_chunking.constants import ChunkingRunStatus
from apps.document_chunking.engine import generate_chunks
from apps.document_chunking.exceptions import ChunkingFailedError
from apps.document_chunking.models import ChunkingRun, DocumentChunk
from apps.document_chunking.services.ownership import validate_training_job_document_alignment
from apps.document_chunking.tokenizer.factory import get_tokenizer
from apps.document_chunking.validation.chunks import validate_chunk_drafts
from apps.document_extraction.models import ExtractionRun
from apps.knowledge.models import KnowledgeVisibility
from apps.training_jobs.models import TrainingJob, TrainingJobStatus

logger = logging.getLogger(__name__)


def _ensure_not_cancelled(job: TrainingJob) -> None:
    job.refresh_from_db()
    if job.status == TrainingJobStatus.CANCELLED:
        raise ChunkingFailedError('Training job was cancelled.')


def run_chunking_for_extraction_run(
    *,
    job: TrainingJob,
    extraction_run: ExtractionRun,
    progress_callback=None,
) -> ChunkingRun:
    validate_training_job_document_alignment(job)
    _ensure_not_cancelled(job)

    config = get_chunking_config()
    existing = ChunkingRun.objects.filter(
        extraction_run=extraction_run,
        chunking_version=config.chunking_version,
    ).first()
    if existing and existing.status == ChunkingRunStatus.SUCCEEDED:
        logger.info(
            'chunking_skip_existing run_id=%s chunking_run_id=%s',
            extraction_run.id,
            existing.id,
        )
        return existing

    bundle = load_bundle_for_run(extraction_run)
    validate_extraction_run_for_chunking(job=job, run=extraction_run, bundle=bundle)

    if progress_callback:
        progress_callback(stage='chunk', progress=50)

    tokenizer = get_tokenizer()
    drafts = generate_chunks(bundle, config=config, tokenizer=tokenizer)
    validate_chunk_drafts(drafts, config=config)

    document = job.document
    now = datetime.now(timezone.utc)

    with transaction.atomic():
        chunking_run, _created = ChunkingRun.objects.select_for_update().get_or_create(
            extraction_run=extraction_run,
            chunking_version=config.chunking_version,
            defaults={
                'status': ChunkingRunStatus.RUNNING,
                'config_snapshot': asdict(config),
                'started_at': now,
            },
        )
        if chunking_run.status == ChunkingRunStatus.SUCCEEDED:
            return chunking_run

        chunking_run.status = ChunkingRunStatus.RUNNING
        chunking_run.error_message = ''
        chunking_run.started_at = chunking_run.started_at or now
        chunking_run.config_snapshot = asdict(config)
        chunking_run.save()

        DocumentChunk.objects.filter(chunking_run=chunking_run).delete()

        batch: list[DocumentChunk] = []
        for draft in drafts:
            batch.append(
                DocumentChunk(
                    chunking_run=chunking_run,
                    extraction_run=extraction_run,
                    document=document,
                    user=job.user,
                    business_model=job.business_model,
                    chunking_version=config.chunking_version,
                    chunk_index=draft.chunk_index,
                    content=draft.content,
                    content_hash=draft.content_hash,
                    token_count=draft.token_count,
                    element_type=draft.element_type,
                    source_type=bundle.source.input_type,
                    visibility=KnowledgeVisibility.PRIVATE,
                    source_location=draft.source_location,
                    lineage=draft.lineage,
                )
            )
            if len(batch) >= config.db_batch_size:
                DocumentChunk.objects.bulk_create(batch)
                batch = []
        if batch:
            DocumentChunk.objects.bulk_create(batch)

        for chunk in DocumentChunk.objects.filter(chunking_run=chunking_run):
            chunk.full_clean()

        chunking_run.chunk_count = len(drafts)
        chunking_run.status = ChunkingRunStatus.SUCCEEDED
        chunking_run.completed_at = datetime.now(timezone.utc)
        chunking_run.save()

    if progress_callback:
        progress_callback(stage='chunk_persisted', progress=70)

    logger.info(
        'chunking_succeeded job_id=%s run_id=%s chunks=%s',
        job.id,
        extraction_run.id,
        len(drafts),
    )
    return chunking_run
