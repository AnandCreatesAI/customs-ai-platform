from __future__ import annotations

import hashlib
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.conf import settings

from apps.document_extraction.schema.serialize import bundle_to_json
from apps.document_extraction.schema.types import ExtractionBundle


def get_extraction_storage():
    return storages[settings.EXTRACTION_STORAGE_ALIAS]


def build_artifact_storage_key(
    *,
    user_id: int,
    business_model_key: str,
    document_id: str,
    artifact_version: int,
    run_id: str,
) -> str:
    return (
        f'extraction_artifacts/{user_id}/{business_model_key}/'
        f'{document_id}/v{artifact_version}/{run_id}.json'
    )


def save_artifact_bundle(
    *,
    user_id: int,
    business_model_key: str,
    bundle: ExtractionBundle,
    artifact_version: int,
) -> tuple[str, str, int]:
    storage = get_extraction_storage()
    payload = bundle_to_json(bundle)
    encoded = payload.encode('utf-8')
    digest = hashlib.sha256(encoded).hexdigest()
    key = build_artifact_storage_key(
        user_id=user_id,
        business_model_key=business_model_key,
        document_id=bundle.document_id,
        artifact_version=artifact_version,
        run_id=bundle.extraction_run_id,
    )
    if storage.exists(key):
        storage.delete(key)
    storage.save(key, ContentFile(encoded))
    return key, digest, len(encoded)


def load_artifact_json(storage_key: str) -> str:
    storage = get_extraction_storage()
    with storage.open(storage_key, 'rb') as handle:
        return handle.read().decode('utf-8')
