import os

from django.conf import settings


def ocr_min_confidence() -> float:
    return float(getattr(settings, 'EXTRACTION_OCR_MIN_CONFIDENCE', 0.35))


def ocr_language() -> str:
    return getattr(settings, 'EXTRACTION_OCR_LANGUAGE', 'eng')


def vision_enabled() -> bool:
    return getattr(settings, 'VISION_ENABLED', False)


def max_elements() -> int:
    return int(getattr(settings, 'EXTRACTION_MAX_ELEMENTS', 50_000))


def max_artifact_bytes() -> int:
    return int(getattr(settings, 'EXTRACTION_MAX_ARTIFACT_BYTES', 25 * 1024 * 1024))


def libreoffice_timeout_seconds() -> int:
    return int(getattr(settings, 'EXTRACTION_LIBREOFFICE_TIMEOUT_SECONDS', 120))


def ocr_timeout_seconds() -> int:
    return int(getattr(settings, 'EXTRACTION_OCR_TIMEOUT_SECONDS', 60))


def pdf_native_min_chars_per_page() -> int:
    return int(getattr(settings, 'EXTRACTION_PDF_NATIVE_MIN_CHARS', 32))


def use_mock_ocr() -> bool:
    return getattr(settings, 'EXTRACTION_USE_MOCK_OCR', False)
