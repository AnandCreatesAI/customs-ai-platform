from __future__ import annotations

from apps.document_extraction.base import DocumentExtractor, ExtractionError

_EXTRACTORS: dict[str, DocumentExtractor] = {}


def register_extractor(extractor: DocumentExtractor) -> None:
    key = extractor.key
    if key in _EXTRACTORS:
        raise ExtractionError(f'Extractor already registered: {key}')
    _EXTRACTORS[key] = extractor


def get_extractor(key: str) -> DocumentExtractor:
    try:
        return _EXTRACTORS[key]
    except KeyError as exc:
        raise ExtractionError(f'No extractor registered for key: {key}') from exc


def registered_extractor_keys() -> list[str]:
    return sorted(_EXTRACTORS.keys())
