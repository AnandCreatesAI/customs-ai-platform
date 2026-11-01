"""
Central file validation for training uploads (all BusinessModel keys).

Does not perform malware scanning or antivirus checks.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import BinaryIO

from apps.documents.training_file_policy import (
    EXPECTED_MIME_BY_EXTENSION,
    EXTENSION_DISPLAY_ORDER,
    TRAINING_ALLOWED_EXTENSIONS,
    TRAINING_MAX_FILE_SIZE_BYTES,
    training_max_file_size_label,
)

_UNSAFE_FILENAME_PATTERN = re.compile(r'[\x00-\x1f\\/:|<>*?"\']')


class FileValidationError(Exception):
    """User-facing validation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class ValidatedTrainingFile:
    display_filename: str
    extension: str
    mime_type: str
    size: int


def normalize_original_filename(raw_name: str) -> str:
    if not raw_name or not str(raw_name).strip():
        raise FileValidationError('Filename is required.')

    raw = str(raw_name).strip()
    if '..' in raw:
        raise FileValidationError('Filename must not contain path traversal sequences.')

    name = os.path.basename(raw)
    if not name or name in {'.', '..'}:
        raise FileValidationError('Filename is not valid.')

    if '..' in name:
        raise FileValidationError('Filename must not contain path traversal sequences.')

    if _UNSAFE_FILENAME_PATTERN.search(name):
        raise FileValidationError('Filename contains unsupported characters.')

    return name


def extension_from_filename(filename: str) -> str:
    normalized = normalize_original_filename(filename)
    if '.' not in normalized:
        return ''
    return normalized.rsplit('.', 1)[-1].lower()


def _file_size(file_obj: BinaryIO) -> int:
    position = file_obj.tell()
    try:
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
    finally:
        file_obj.seek(position)
    return size


def _read_prefix(file_obj: BinaryIO, max_bytes: int = 8192) -> bytes:
    position = file_obj.tell()
    try:
        file_obj.seek(0)
        return file_obj.read(max_bytes)
    finally:
        file_obj.seek(position)


def _detect_mime_from_content(prefix: bytes, extension: str) -> str | None:
    if extension == 'pdf':
        return 'application/pdf' if prefix.startswith(b'%PDF') else None

    if extension in {'docx', 'xlsx'}:
        return (
            'application/zip'
            if prefix.startswith(b'PK\x03\x04')
            else None
        )

    if extension in {'doc', 'xls'}:
        return (
            'application/octet-stream'
            if prefix.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
            else None
        )

    if extension == 'json':
        stripped = prefix.lstrip()
        if stripped.startswith((b'{', b'[')):
            return 'application/json'
        return None

    if extension in {'txt', 'csv'}:
        if b'\x00' in prefix:
            return None
        return 'text/plain'

    if extension == 'png':
        return 'image/png' if prefix.startswith(b'\x89PNG\r\n\x1a\n') else None

    if extension in {'jpg', 'jpeg'}:
        return 'image/jpeg' if prefix.startswith(b'\xff\xd8\xff') else None

    if extension in {'tiff', 'tif'}:
        return (
            'image/tiff'
            if prefix.startswith((b'II*\x00', b'MM\x00*'))
            else None
        )

    return None


def _content_matches_extension(prefix: bytes, extension: str, *, size: int) -> bool:
    if size == 0:
        return False

    if extension == 'json':
        return bool(prefix.lstrip().startswith((b'{', b'[')))

    return _detect_mime_from_content(prefix, extension) is not None


def _validate_json_body(file_obj: BinaryIO, size: int) -> None:
    position = file_obj.tell()
    try:
        file_obj.seek(0)
        raw = file_obj.read(size)
    finally:
        file_obj.seek(position)

    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise FileValidationError('JSON file must be UTF-8 encoded.') from exc

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FileValidationError('JSON file is not valid JSON.') from exc

    if not isinstance(parsed, (dict, list)):
        raise FileValidationError('JSON must be a top-level object or array.')


def validate_training_upload(
    file_obj: BinaryIO,
    original_filename: str,
    *,
    claimed_content_type: str | None = None,
) -> ValidatedTrainingFile:
    """
    Validate an uploaded file object before storage.

    Uses size checks, extension allowlist, filename safety, and basic content sniffing.
    Browser-provided MIME types are not trusted alone.
    """
    display_filename = normalize_original_filename(original_filename)
    extension = extension_from_filename(display_filename)

    if not extension:
        raise FileValidationError(
            f'{display_filename}: file must have a supported extension.'
        )

    if extension not in TRAINING_ALLOWED_EXTENSIONS:
        allowed = ', '.join(ext.upper() for ext in EXTENSION_DISPLAY_ORDER)
        raise FileValidationError(
            f'{display_filename}: unsupported type. Allowed: {allowed}.'
        )

    size = _file_size(file_obj)
    if size == 0:
        raise FileValidationError(f'{display_filename}: file is empty.')

    if size > TRAINING_MAX_FILE_SIZE_BYTES:
        limit_label = training_max_file_size_label()
        raise FileValidationError(f'{display_filename}: exceeds the {limit_label} limit.')

    prefix = _read_prefix(file_obj)
    if not _content_matches_extension(prefix, extension, size=size):
        raise FileValidationError(
            f'{display_filename}: file content does not match the {extension.upper()} type.'
        )

    if extension == 'json':
        _validate_json_body(file_obj, size)

    sniffed = _detect_mime_from_content(prefix, extension) or 'application/octet-stream'
    expected = EXPECTED_MIME_BY_EXTENSION.get(extension, ())
    if claimed_content_type:
        claimed = claimed_content_type.split(';', 1)[0].strip().lower()
        if claimed and claimed not in expected and claimed != sniffed.lower():
            raise FileValidationError(
                f'{display_filename}: reported content type does not match the file.'
            )

    mime_type = sniffed
    if mime_type == 'application/octet-stream' and expected:
        mime_type = expected[0]

    return ValidatedTrainingFile(
        display_filename=display_filename,
        extension=extension,
        mime_type=mime_type,
        size=size,
    )
