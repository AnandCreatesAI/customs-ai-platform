from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from django.db import transaction

from apps.documents.document_storage import get_document_storage
from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.models import ExtractionRun, ExtractionRunStatus
from apps.document_extraction.normalization.pipeline import normalize_elements
from apps.document_extraction.ocr.engine import run_ocr_on_image
from apps.document_extraction.registry import get_extractor
from apps.document_extraction.routing import resolve_extractor_key
from apps.document_extraction.schema.types import (
    Element,
    ExtractionBundle,
    PipelineInfo,
    QualityResult,
    SourceRef,
)
from apps.document_extraction.schema.version import SCHEMA_VERSION
from apps.document_extraction.schema.serialize import bundle_to_json
from apps.document_extraction.storage.artifacts import save_artifact_bundle
from apps.document_extraction.storage.temp_workspace import job_workspace
from apps.document_extraction.validation.quality import validate_extraction_quality
from apps.document_extraction.vision.service import maybe_apply_vision
from apps.training_jobs.models import TrainingJob, TrainingJobStatus

logger = logging.getLogger(__name__)


class ExtractionFailedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _update_job_stage(job: TrainingJob, stage: str, progress: int) -> None:
    job.current_stage = stage
    job.progress = progress
    job.save(update_fields=['current_stage', 'progress', 'updated_at'])


def _next_artifact_version(document_id) -> int:
    latest = (
        ExtractionRun.objects.filter(document_id=document_id)
        .order_by('-artifact_version')
        .values_list('artifact_version', flat=True)
        .first()
    )
    return (latest or 0) + 1


def _materialize_document(document, destination: Path) -> None:
    storage = get_document_storage()
    with storage.open(document.file_path, 'rb') as handle:
        destination.write_bytes(handle.read())


def _ocr_docx_embedded_images(elements: list[Element], methods: list[str]) -> list[Element]:
    output: list[Element] = list(elements)
    for element in elements:
        if element.kind != 'image_ref':
            continue
        media_path = (element.structured_data or {}).get('media_path')
        if not media_path:
            continue
        path = Path(media_path)
        if not path.exists():
            continue
        if 'ocr' not in methods:
            methods.append('ocr')
        for block in run_ocr_on_image(path):
            output.append(
                Element(
                    element_id=new_element_id(),
                    kind='ocr_block',
                    text=block.text,
                    parent_element_id=element.element_id,
                    extraction_method='ocr',
                    confidence=block.confidence,
                )
            )
    return output


def run_for_job(job: TrainingJob) -> ExtractionRun:
    if job.status not in {TrainingJobStatus.PROCESSING}:
        raise ExtractionFailedError('Training job is not in processing state.')

    job.refresh_from_db()
    if job.status == TrainingJobStatus.CANCELLED:
        raise ExtractionFailedError('Training job was cancelled.')

    document = job.document
    extractor_key = resolve_extractor_key(document)
    run_id = None
    artifact_key = ''

    with job_workspace(str(job.id)) as workspace:
        _update_job_stage(job, 'resolve_document', 8)
        input_path = workspace / f'input.{document.file_type or "bin"}'
        _materialize_document(document, input_path)

        _update_job_stage(job, 'prepare_workspace', 12)
        ctx = ExtractionContext(document=document, input_path=input_path, workspace=workspace)

        if extractor_key in {'doc', 'xls'}:
            _update_job_stage(job, 'convert_legacy', 16)

        _update_job_stage(job, 'extract', 22)
        try:
            elements = get_extractor(extractor_key).extract(ctx)
        except ExtractionError as exc:
            raise ExtractionFailedError(exc.message) from exc

        if extractor_key == 'docx':
            _update_job_stage(job, 'ocr', 30)
            elements = _ocr_docx_embedded_images(elements, ctx.methods_used)

        if extractor_key in {'pdf', 'image'} and 'ocr' in ctx.methods_used:
            _update_job_stage(job, 'ocr', 30)

        _update_job_stage(job, 'vision_optional', 34)
        elements = maybe_apply_vision(ctx, elements)

        _update_job_stage(job, 'normalize', 38)
        elements = normalize_elements(elements)

        input_type = (document.metadata or {}).get('input_type', 'file')
        provisional_bundle = ExtractionBundle(
            schema_version=SCHEMA_VERSION,
            extraction_run_id='pending',
            training_job_id=str(job.id),
            document_id=str(document.id),
            business_model_key=document.business_model.key,
            source=SourceRef(
                original_filename=document.original_filename,
                file_type=document.file_type,
                input_type=str(input_type),
                storage_key=document.file_path,
                checksum_sha256=document.checksum,
                byte_size=document.file_size,
            ),
            pipeline=PipelineInfo(extractor_key=extractor_key, methods=ctx.methods_used),
            quality=QualityResult(
                meaningful_content=False,
                quality_passed=False,
                quality_score=0.0,
            ),
            elements=elements,
        )
        artifact_bytes = len(bundle_to_json(provisional_bundle).encode('utf-8'))

        _update_job_stage(job, 'validate_quality', 41)
        quality = validate_extraction_quality(elements, artifact_byte_size=artifact_bytes)
        if quality.review_required:
            quality.errors.append('Extraction requires review due to low OCR confidence.')
            quality.quality_passed = False
        if not quality.quality_passed:
            message = quality.errors[0] if quality.errors else 'Extraction quality validation failed.'
            raise ExtractionFailedError(message)

        _update_job_stage(job, 'persist_artifact', 43)
        artifact_version = _next_artifact_version(document.id)

        with transaction.atomic():
            run = ExtractionRun(
                training_job=job,
                document=document,
                user=job.user,
                business_model=job.business_model,
                status=ExtractionRunStatus.RUNNING,
                schema_version=SCHEMA_VERSION,
                extractor_key=extractor_key,
                artifact_version=artifact_version,
            )
            run.full_clean()
            run.save()
            run_id = str(run.id)

            bundle = ExtractionBundle(
                schema_version=SCHEMA_VERSION,
                extraction_run_id=run_id,
                training_job_id=str(job.id),
                document_id=str(document.id),
                business_model_key=document.business_model.key,
                source=provisional_bundle.source,
                pipeline=provisional_bundle.pipeline,
                quality=quality,
                elements=elements,
            )
            try:
                artifact_key, checksum, byte_size = save_artifact_bundle(
                    user_id=job.user_id,
                    business_model_key=document.business_model.key,
                    bundle=bundle,
                    artifact_version=artifact_version,
                )
            except Exception as exc:
                raise ExtractionFailedError('Failed to persist extraction artifact.') from exc

            run.status = ExtractionRunStatus.SUCCEEDED
            run.artifact_storage_key = artifact_key
            run.artifact_checksum = checksum
            run.artifact_byte_size = byte_size
            run.quality_passed = quality.quality_passed
            run.meaningful_content = quality.meaningful_content
            run.summary = {
                'element_count': len(elements),
                'methods': ctx.methods_used,
            }
            run.completed_at = datetime.now(timezone.utc)
            run.save()

    _update_job_stage(job, 'extraction_complete', 45)
    logger.info(
        'extraction_succeeded job_id=%s run_id=%s artifact_key=%s',
        job.id,
        run_id,
        artifact_key,
    )
    return ExtractionRun.objects.get(pk=run_id)
