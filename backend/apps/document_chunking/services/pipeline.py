from __future__ import annotations

from apps.document_chunking.exceptions import ChunkingFailedError, EmbeddingFailedError
from apps.document_chunking.services.run_chunking import run_chunking_for_extraction_run
from apps.document_chunking.services.run_embeddings import run_embeddings_for_chunking_run
from apps.document_extraction.models import ExtractionRun
from apps.training_jobs.models import TrainingJob


def _update_progress(job: TrainingJob, *, stage: str, progress: int) -> None:
    job.current_stage = stage
    job.progress = progress
    job.save(update_fields=['current_stage', 'progress', 'updated_at'])


def run_chunk_and_embed_for_job(job: TrainingJob, extraction_run: ExtractionRun) -> None:
    def progress_callback(*, stage: str, progress: int) -> None:
        _update_progress(job, stage=stage, progress=progress)

    try:
        chunking_run = run_chunking_for_extraction_run(
            job=job,
            extraction_run=extraction_run,
            progress_callback=progress_callback,
        )
    except ChunkingFailedError:
        raise
    except Exception as exc:
        raise ChunkingFailedError(str(exc)) from exc

    try:
        run_embeddings_for_chunking_run(
            job=job,
            chunking_run=chunking_run,
            progress_callback=progress_callback,
        )
    except EmbeddingFailedError:
        raise
    except Exception as exc:
        raise EmbeddingFailedError(str(exc)) from exc

    _update_progress(job, stage='finalize', progress=100)
