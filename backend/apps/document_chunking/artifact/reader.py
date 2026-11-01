from __future__ import annotations

from apps.document_extraction.models import ExtractionRun
from apps.document_extraction.schema.serialize import bundle_from_json
from apps.document_extraction.schema.types import ExtractionBundle
from apps.document_extraction.storage.artifacts import load_artifact_json
from apps.document_chunking.exceptions import ChunkingFailedError


def load_bundle_for_run(run: ExtractionRun) -> ExtractionBundle:
    if not run.artifact_storage_key:
        raise ChunkingFailedError('Extraction run has no artifact storage key.')
    try:
        payload = load_artifact_json(run.artifact_storage_key)
    except Exception as exc:
        raise ChunkingFailedError('Failed to load extraction artifact.') from exc
    try:
        bundle = bundle_from_json(payload)
    except Exception as exc:
        raise ChunkingFailedError('Extraction artifact failed schema validation.') from exc
    return bundle
