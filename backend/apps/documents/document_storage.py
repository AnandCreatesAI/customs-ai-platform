"""
Secure document storage for training files (all BusinessModel keys).

Uses Django's storage API (`storages[DOCUMENT_STORAGE_ALIAS]`). Binary content never
goes to PostgreSQL; `Document.file_path` stores the storage key returned here.

Future upload APIs must pass `user=request.user` and resolve `BusinessModel` server-side;
never accept a client-supplied owner user id for storage paths.

Future delete APIs should use ``delete_stored_document`` after authorization so storage
keys are removed when metadata rows are deleted.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from typing import BinaryIO

from django.core.files.base import File
from django.core.files.storage import storages
from django.db import transaction

from django.core.exceptions import ValidationError as DjangoValidationError

from apps.documents.file_validation import (
    FileValidationError,
    ValidatedTrainingFile,
    normalize_original_filename,
    validate_training_upload,
)
from apps.documents.models import Document, DocumentStatus
from apps.documents.training_input_validation import (
    validate_training_json_content,
    validate_training_json_title,
    validate_training_text_content,
    validate_training_text_title,
)
from apps.model_management.models import BusinessModel


class DocumentStorageError(Exception):
    pass


def get_document_storage():
    from django.conf import settings

    return storages[settings.DOCUMENT_STORAGE_ALIAS]


def generate_storage_filename(extension: str) -> str:
    safe_ext = (extension or '').strip().lower().lstrip('.')
    if not safe_ext:
        safe_ext = 'bin'
    return f'{uuid.uuid4().hex}.{safe_ext}'


def build_document_storage_key(
    *,
    user_id: int,
    business_model_key: str,
    generated_filename: str,
    uploaded_at: datetime | None = None,
) -> str:
    if not business_model_key or '/' in business_model_key or '\\' in business_model_key:
        raise DocumentStorageError('Invalid business model key for storage path.')

    if '..' in generated_filename or '/' in generated_filename or '\\' in generated_filename:
        raise DocumentStorageError('Invalid generated storage filename.')

    moment = uploaded_at or datetime.now(timezone.utc)
    return (
        f'documents/{user_id}/{business_model_key}/'
        f'{moment.year:04d}/{moment.month:02d}/{generated_filename}'
    )


def _checksum_sha256(file_obj: BinaryIO) -> str:
    digest = hashlib.sha256()
    position = file_obj.tell()
    try:
        file_obj.seek(0)
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        file_obj.seek(position)
    return digest.hexdigest()


def save_validated_file_to_storage(
    *,
    user_id: int,
    business_model: BusinessModel,
    validated: ValidatedTrainingFile,
    file_obj: BinaryIO,
    uploaded_at: datetime | None = None,
) -> tuple[str, str]:
    storage = get_document_storage()
    generated_name = generate_storage_filename(validated.extension)
    storage_key = build_document_storage_key(
        user_id=user_id,
        business_model_key=business_model.key,
        generated_filename=generated_name,
        uploaded_at=uploaded_at,
    )
    checksum = _checksum_sha256(file_obj)

    file_obj.seek(0)
    try:
        storage.save(storage_key, File(file_obj))
    except Exception as exc:
        raise DocumentStorageError('Failed to save file to storage.') from exc

    return storage_key, checksum


def delete_storage_object(storage_key: str) -> None:
    if not storage_key:
        return
    storage = get_document_storage()
    if storage.exists(storage_key):
        storage.delete(storage_key)


def delete_stored_document(document: Document) -> None:
    """
    Delete a Document row and its stored binary (for future authorized delete APIs).

    Call only after verifying ``document.user`` matches ``request.user`` (and model scope).
    """
    storage_key = document.file_path
    document.delete()
    delete_storage_object(storage_key)


@transaction.atomic
def persist_validated_document(
    *,
    user,
    business_model: BusinessModel,
    validated: ValidatedTrainingFile,
    file_obj: BinaryIO,
    uploaded_at: datetime | None = None,
    metadata: dict | None = None,
) -> Document:
    storage_key: str | None = None
    try:
        storage_key, checksum = save_validated_file_to_storage(
            user_id=user.pk,
            business_model=business_model,
            validated=validated,
            file_obj=file_obj,
            uploaded_at=uploaded_at,
        )
        document = Document(
            user=user,
            business_model=business_model,
            original_filename=validated.display_filename,
            file_type=validated.extension,
            mime_type=validated.mime_type,
            file_path=storage_key,
            file_size=validated.size,
            checksum=checksum,
            status=DocumentStatus.UPLOADED,
            metadata=metadata or {},
        )
        document.full_clean()
        document.save()
        return document
    except Exception:
        if storage_key:
            delete_storage_object(storage_key)
        raise


def store_training_upload(
    *,
    user,
    business_model: BusinessModel,
    file_obj: BinaryIO,
    original_filename: str,
    claimed_content_type: str | None = None,
    metadata: dict | None = None,
) -> Document:
    """
    Validate, store, and persist Document metadata for a training file upload.

    Validation runs before any storage write. If storage succeeds but the database write
    fails, the stored object is removed. Intended for future authenticated upload APIs.
    """
    try:
        validated = validate_training_upload(
            file_obj,
            original_filename,
            claimed_content_type=claimed_content_type,
        )
    except FileValidationError as exc:
        raise DocumentStorageError(str(exc)) from exc

    return persist_validated_document(
        user=user,
        business_model=business_model,
        validated=validated,
        file_obj=file_obj,
        metadata=metadata,
    )


def _validation_error_message(exc: DjangoValidationError) -> str:
    if hasattr(exc, 'message_dict'):
        parts = []
        for messages in exc.message_dict.values():
            parts.extend(messages)
        return ' '.join(str(part) for part in parts)
    if hasattr(exc, 'messages'):
        return ' '.join(str(message) for message in exc.messages)
    return str(exc)


def _training_input_metadata(
    *,
    input_type: str,
    title: str,
    group_title: str | None = None,
) -> dict:
    metadata = {'input_type': input_type, 'title': title}
    if group_title:
        metadata['group_title'] = group_title
    return metadata


def _display_filename_for_title(title: str, extension: str) -> str:
    stem = (title or '').strip() or 'training-input'
    candidate = f'{stem}.{extension}'
    return normalize_original_filename(candidate)


def store_training_text_input(
    *,
    user,
    business_model: BusinessModel,
    title: str,
    content: str,
) -> Document:
    try:
        cleaned_title = validate_training_text_title(title)
        cleaned_content = validate_training_text_content(content)
    except DjangoValidationError as exc:
        raise DocumentStorageError(_validation_error_message(exc)) from exc

    payload = cleaned_content.encode('utf-8')
    file_obj = io.BytesIO(payload)
    return store_training_upload(
        user=user,
        business_model=business_model,
        file_obj=file_obj,
        original_filename=_display_filename_for_title(cleaned_title, 'txt'),
        claimed_content_type='text/plain',
        metadata=_training_input_metadata(input_type='text', title=cleaned_title),
    )


def store_training_json_input(
    *,
    user,
    business_model: BusinessModel,
    title: str,
    content: str,
) -> Document:
    try:
        cleaned_title = validate_training_json_title(title)
        cleaned_content = validate_training_json_content(content)
    except DjangoValidationError as exc:
        raise DocumentStorageError(_validation_error_message(exc)) from exc

    payload = cleaned_content.encode('utf-8')
    file_obj = io.BytesIO(payload)
    return store_training_upload(
        user=user,
        business_model=business_model,
        file_obj=file_obj,
        original_filename=_display_filename_for_title(cleaned_title, 'json'),
        claimed_content_type='application/json',
        metadata=_training_input_metadata(input_type='json', title=cleaned_title),
    )
