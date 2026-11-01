from __future__ import annotations

from apps.document_extraction.conf import max_artifact_bytes, max_elements, ocr_min_confidence
from apps.document_extraction.schema.types import Element, QualityResult
from apps.document_extraction.validation.meaningful_content import has_meaningful_content


def validate_extraction_quality(
    elements: list[Element],
    *,
    artifact_byte_size: int,
) -> QualityResult:
    warnings: list[str] = []
    errors: list[str] = []

    if len(elements) > max_elements():
        errors.append('Element count exceeds configured limit.')
    if artifact_byte_size > max_artifact_bytes():
        errors.append('Artifact size exceeds configured limit.')

    meaningful = has_meaningful_content(elements)
    if not meaningful:
        errors.append('No meaningful content extracted.')

    low_confidence = False
    for element in elements:
        if element.extraction_method == 'ocr' and element.confidence is not None:
            if element.confidence < ocr_min_confidence():
                low_confidence = True
                warnings.append(
                    f'Low OCR confidence on element {element.element_id}.'
                )

    review_required = low_confidence and meaningful
    quality_score = 1.0
    if low_confidence:
        quality_score = 0.5
    if errors:
        quality_score = 0.0

    passed = meaningful and not errors and not review_required
    return QualityResult(
        meaningful_content=meaningful,
        quality_passed=passed,
        quality_score=quality_score,
        warnings=warnings,
        errors=errors,
        review_required=review_required,
    )
