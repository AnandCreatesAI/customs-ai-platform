from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ELEMENT_KINDS = frozenset(
    {
        'heading',
        'paragraph',
        'list_item',
        'table',
        'table_row',
        'table_cell',
        'sheet',
        'sheet_row',
        'field',
        'json_value',
        'image_ref',
        'ocr_block',
        'vision_block',
    }
)

EXTRACTION_METHODS = frozenset(
    {
        'native',
        'ocr',
        'libreoffice',
        'parsed',
        'openpyxl',
        'python_docx',
        'pypdf',
        'pdfplumber',
        'vision',
    }
)


@dataclass
class SourceRef:
    original_filename: str
    file_type: str
    input_type: str
    storage_key: str
    checksum_sha256: str
    byte_size: int


@dataclass
class LocationRef:
    page: int | None = None
    bbox: list[float] | None = None
    sheet_name: str | None = None
    row_index: int | None = None
    column_index: int | None = None
    json_path: str | None = None
    paragraph_index: int | None = None
    block_index: int | None = None


@dataclass
class Element:
    element_id: str
    kind: str
    text: str | None = None
    structured_data: dict[str, Any] | None = None
    source_location: LocationRef | None = None
    extraction_method: str = 'parsed'
    confidence: float | None = None
    parent_element_id: str | None = None
    normalized_text: str | None = None


@dataclass
class QualityResult:
    meaningful_content: bool
    quality_passed: bool
    quality_score: float
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    review_required: bool = False


@dataclass
class PipelineInfo:
    extractor_key: str
    methods: list[str] = field(default_factory=list)


@dataclass
class ExtractionBundle:
    schema_version: str
    extraction_run_id: str
    training_job_id: str
    document_id: str
    business_model_key: str
    source: SourceRef
    pipeline: PipelineInfo
    quality: QualityResult
    elements: list[Element] = field(default_factory=list)
