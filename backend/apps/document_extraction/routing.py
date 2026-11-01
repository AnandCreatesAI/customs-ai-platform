from __future__ import annotations

from apps.documents.models import Document
from apps.document_extraction.base import ExtractionError

_IMAGE_EXTENSIONS = frozenset({'png', 'jpg', 'jpeg', 'tiff', 'tif'})


def resolve_extractor_key(document: Document) -> str:
    file_type = (document.file_type or '').lower().strip()
    input_type = (document.metadata or {}).get('input_type', 'file')
    if input_type == 'text' or file_type == 'txt':
        return 'txt'
    if input_type == 'json' or file_type == 'json':
        return 'json'
    mapping = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'doc',
        'xlsx': 'xlsx',
        'xls': 'xls',
        'csv': 'csv',
    }
    if file_type in mapping:
        return mapping[file_type]
    if file_type in _IMAGE_EXTENSIONS:
        return 'image'
    raise ExtractionError(f'Unsupported document type for extraction: {file_type or "unknown"}')
