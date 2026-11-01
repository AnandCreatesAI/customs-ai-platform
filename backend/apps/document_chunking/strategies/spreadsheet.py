from __future__ import annotations

import json
from collections import defaultdict

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_extraction.schema.types import Element
from apps.document_chunking.strategies._helpers import location_to_dict

_SHEET_KINDS = frozenset({'sheet', 'sheet_row'})


class SpreadsheetChunkStrategy:
    name = 'spreadsheet'

    def matches(self, profile: FormatProfile) -> bool:
        return profile.has_sheets or profile.extractor_key in {'xlsx', 'xls', 'csv'}

    def select_element_ids(
        self,
        profile: FormatProfile,
        elements: list[Element],
        assigned: set[str],
    ) -> list[Element]:
        selected: list[Element] = []
        for element in elements:
            if element.element_id in assigned:
                continue
            if element.kind in _SHEET_KINDS:
                selected.append(element)
                assigned.add(element.element_id)
        return selected

    def _format_row(self, element: Element) -> str:
        structured = element.structured_data or {}
        if structured:
            return json.dumps(structured, ensure_ascii=False, sort_keys=True)
        return element.text or ''

    def chunk(
        self,
        *,
        profile: FormatProfile,
        elements: list[Element],
        config: ChunkingConfig,
        tokenizer,
        start_index: int,
    ) -> tuple[list[ChunkDraft], int]:
        rows = [element for element in elements if element.kind == 'sheet_row']
        if not rows:
            return [], start_index

        max_rows = max(1, config.spreadsheet_max_rows)
        by_sheet: dict[str, list[Element]] = defaultdict(list)
        for row in rows:
            sheet = ''
            if row.source_location and row.source_location.sheet_name:
                sheet = row.source_location.sheet_name
            by_sheet[sheet].append(row)

        chunks: list[ChunkDraft] = []
        index = start_index
        for sheet_name, sheet_rows in by_sheet.items():
            for offset in range(0, len(sheet_rows), max_rows):
                batch = sheet_rows[offset : offset + max_rows]
                lines = [self._format_row(row) for row in batch]
                content = '\n'.join(line for line in lines if line)
                if not content:
                    continue
                primary = batch[0]
                location = location_to_dict(primary.source_location)
                if sheet_name:
                    location.setdefault('sheet_name', sheet_name)
                chunks.append(
                    ChunkDraft(
                        chunk_index=index,
                        content=content,
                        token_count=tokenizer.count_tokens(content),
                        element_type='sheet_row',
                        source_location=location,
                        lineage={
                            'element_ids': [row.element_id for row in batch],
                            'parent_element_id': primary.parent_element_id,
                            'sheet_name': sheet_name or None,
                        },
                    )
                )
                index += 1
        return chunks, index
