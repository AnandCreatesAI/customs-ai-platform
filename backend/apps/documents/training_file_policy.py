"""
Central training file policy shared by all BusinessModel keys.

Environment overrides keep limits configurable without code changes.
"""

import os

TRAINING_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        'pdf',
        'docx',
        'doc',
        'txt',
        'xlsx',
        'xls',
        'csv',
        'json',
        'png',
        'jpg',
        'jpeg',
        'tiff',
        'tif',
    }
)

_DEFAULT_MAX_BYTES = 25 * 1024 * 1024  # 26,214,400 bytes

TRAINING_MAX_FILE_SIZE_BYTES: int = int(
    os.environ.get('TRAINING_MAX_FILE_SIZE_BYTES', str(_DEFAULT_MAX_BYTES))
)


def training_max_file_size_label() -> str:
    megabytes = TRAINING_MAX_FILE_SIZE_BYTES / (1024 * 1024)
    if megabytes.is_integer():
        return f'{int(megabytes)} MB'
    return f'{megabytes:.1f} MB'

TRAINING_TEXT_MAX_CHARS: int = int(os.environ.get('TRAINING_TEXT_MAX_CHARS', '500000'))

TRAINING_JSON_MAX_CHARS: int = int(os.environ.get('TRAINING_JSON_MAX_CHARS', '500000'))

EXTENSION_DISPLAY_ORDER: tuple[str, ...] = (
    'pdf',
    'docx',
    'doc',
    'txt',
    'xlsx',
    'xls',
    'csv',
    'json',
    'png',
    'jpg',
    'jpeg',
    'tiff',
)

EXPECTED_MIME_BY_EXTENSION: dict[str, tuple[str, ...]] = {
    'pdf': ('application/pdf',),
    'docx': (
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/zip',
    ),
    'doc': ('application/msword', 'application/x-msword', 'application/octet-stream'),
    'txt': ('text/plain', 'application/octet-stream'),
    'xlsx': (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/zip',
    ),
    'xls': ('application/vnd.ms-excel', 'application/octet-stream'),
    'csv': ('text/csv', 'text/plain', 'application/csv', 'application/octet-stream'),
    'json': ('application/json', 'text/json', 'application/octet-stream', 'text/plain'),
    'png': ('image/png', 'application/octet-stream'),
    'jpg': ('image/jpeg', 'application/octet-stream'),
    'jpeg': ('image/jpeg', 'application/octet-stream'),
    'tiff': ('image/tiff', 'application/octet-stream'),
    'tif': ('image/tiff', 'application/octet-stream'),
}
