"""
Generic training job processing interface (all BusinessModel keys).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from apps.training_jobs.models import TrainingJob


class ProcessingPipelineNotReadyError(Exception):
    """Raised when extraction pipeline cannot run."""


@dataclass(frozen=True)
class ProcessingStageUpdate:
    current_stage: str
    progress: int


class TrainingJobProcessor(Protocol):
    def run(self, job: TrainingJob) -> None:
        """Run processing for ``job`` or raise on failure."""


class FullTrainingPipelineProcessor:
    def run(self, job: TrainingJob) -> None:
        from apps.document_extraction.services.run_extraction import run_for_job
        from apps.document_chunking.services.pipeline import run_chunk_and_embed_for_job

        extraction_run = run_for_job(job)
        run_chunk_and_embed_for_job(job, extraction_run)


def get_training_job_processor() -> TrainingJobProcessor:
    return FullTrainingPipelineProcessor()
