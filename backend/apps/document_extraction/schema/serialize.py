from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from apps.document_extraction.schema.types import (
    ELEMENT_KINDS,
    Element,
    ExtractionBundle,
    LocationRef,
    PipelineInfo,
    QualityResult,
    SourceRef,
)


class SchemaValidationError(Exception):
    pass


def _location_to_dict(loc: LocationRef | None) -> dict[str, Any] | None:
    if loc is None:
        return None
    return {k: v for k, v in asdict(loc).items() if v is not None}


def element_to_dict(element: Element) -> dict[str, Any]:
    payload = {
        'element_id': element.element_id,
        'kind': element.kind,
        'text': element.text,
        'structured_data': element.structured_data,
        'source_location': _location_to_dict(element.source_location),
        'extraction_method': element.extraction_method,
        'confidence': element.confidence,
        'parent_element_id': element.parent_element_id,
        'normalized_text': element.normalized_text,
    }
    return {k: v for k, v in payload.items() if v is not None}


def bundle_to_dict(bundle: ExtractionBundle) -> dict[str, Any]:
    return {
        'schema_version': bundle.schema_version,
        'extraction_run_id': bundle.extraction_run_id,
        'training_job_id': bundle.training_job_id,
        'document_id': bundle.document_id,
        'business_model_key': bundle.business_model_key,
        'source': asdict(bundle.source),
        'pipeline': {
            'extractor_key': bundle.pipeline.extractor_key,
            'methods': bundle.pipeline.methods,
        },
        'quality': asdict(bundle.quality),
        'elements': [element_to_dict(el) for el in bundle.elements],
    }


def bundle_to_json(bundle: ExtractionBundle) -> str:
    return json.dumps(bundle_to_dict(bundle), ensure_ascii=False, separators=(',', ':'))


def _location_from_dict(data: dict[str, Any] | None) -> LocationRef | None:
    if not data:
        return None
    return LocationRef(
        page=data.get('page'),
        bbox=data.get('bbox'),
        sheet_name=data.get('sheet_name'),
        row_index=data.get('row_index'),
        column_index=data.get('column_index'),
        json_path=data.get('json_path'),
        paragraph_index=data.get('paragraph_index'),
        block_index=data.get('block_index'),
    )


def element_from_dict(data: dict[str, Any]) -> Element:
    kind = data.get('kind', '')
    if kind not in ELEMENT_KINDS:
        raise SchemaValidationError(f'Invalid element kind: {kind}')
    return Element(
        element_id=str(data['element_id']),
        kind=kind,
        text=data.get('text'),
        structured_data=data.get('structured_data'),
        source_location=_location_from_dict(data.get('source_location')),
        extraction_method=str(data.get('extraction_method', 'parsed')),
        confidence=data.get('confidence'),
        parent_element_id=data.get('parent_element_id'),
        normalized_text=data.get('normalized_text'),
    )


def bundle_from_dict(data: dict[str, Any]) -> ExtractionBundle:
    source_data = data['source']
    quality_data = data['quality']
    pipeline_data = data['pipeline']
    return ExtractionBundle(
        schema_version=str(data['schema_version']),
        extraction_run_id=str(data['extraction_run_id']),
        training_job_id=str(data['training_job_id']),
        document_id=str(data['document_id']),
        business_model_key=str(data['business_model_key']),
        source=SourceRef(
            original_filename=source_data['original_filename'],
            file_type=source_data['file_type'],
            input_type=source_data['input_type'],
            storage_key=source_data['storage_key'],
            checksum_sha256=source_data.get('checksum_sha256', ''),
            byte_size=int(source_data['byte_size']),
        ),
        pipeline=PipelineInfo(
            extractor_key=pipeline_data['extractor_key'],
            methods=list(pipeline_data.get('methods', [])),
        ),
        quality=QualityResult(
            meaningful_content=bool(quality_data['meaningful_content']),
            quality_passed=bool(quality_data['quality_passed']),
            quality_score=float(quality_data.get('quality_score', 0.0)),
            warnings=list(quality_data.get('warnings', [])),
            errors=list(quality_data.get('errors', [])),
            review_required=bool(quality_data.get('review_required', False)),
        ),
        elements=[element_from_dict(item) for item in data.get('elements', [])],
    )


def bundle_from_json(raw: str) -> ExtractionBundle:
    return bundle_from_dict(json.loads(raw))
