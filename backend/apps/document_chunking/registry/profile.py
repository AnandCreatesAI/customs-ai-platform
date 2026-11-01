from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from apps.document_extraction.schema.types import ExtractionBundle


@dataclass
class FormatProfile:
    extractor_key: str
    file_type: str
    input_type: str
    element_kind_counts: Counter = field(default_factory=Counter)

    @property
    def has_sheets(self) -> bool:
        return self.element_kind_counts.get('sheet', 0) > 0 or self.element_kind_counts.get(
            'sheet_row', 0
        ) > 0

    @property
    def has_json_paths(self) -> bool:
        return self.element_kind_counts.get('json_value', 0) > 0 or self.element_kind_counts.get(
            'field', 0
        ) > 0

    @property
    def has_tables(self) -> bool:
        return (
            self.element_kind_counts.get('table', 0) > 0
            or self.element_kind_counts.get('table_row', 0) > 0
        )

    @property
    def has_ocr(self) -> bool:
        return (
            self.element_kind_counts.get('ocr_block', 0) > 0
            or self.element_kind_counts.get('vision_block', 0) > 0
        )


def build_format_profile(bundle: ExtractionBundle) -> FormatProfile:
    counts: Counter = Counter()
    for element in bundle.elements:
        counts[element.kind] += 1
    return FormatProfile(
        extractor_key=bundle.pipeline.extractor_key,
        file_type=bundle.source.file_type,
        input_type=bundle.source.input_type,
        element_kind_counts=counts,
    )
