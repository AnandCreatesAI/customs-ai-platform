from __future__ import annotations

import json

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_extraction.schema.types import Element
from apps.document_chunking.strategies._helpers import element_text, lineage_for_element, location_to_dict

_JSON_KINDS = frozenset({'json_value', 'field'})


class JsonRecordsChunkStrategy:
    name = 'json_records'

    def matches(self, profile: FormatProfile) -> bool:
        return profile.has_json_paths or profile.extractor_key == 'json'

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
            if element.kind in _JSON_KINDS:
                selected.append(element)
                assigned.add(element.element_id)
        return selected

    def chunk(
        self,
        *,
        profile: FormatProfile,
        elements: list[Element],
        config: ChunkingConfig,
        tokenizer,
        start_index: int,
    ) -> tuple[list[ChunkDraft], int]:
        chunks: list[ChunkDraft] = []
        index = start_index
        max_tokens = config.json_max_tokens

        for element in elements:
            if element.kind not in _JSON_KINDS:
                continue
            base_text = element_text(element)
            structured = element.structured_data or {}
            if structured and not base_text:
                base_text = json.dumps(structured, ensure_ascii=False, sort_keys=True)
            path = ''
            if element.source_location and element.source_location.json_path:
                path = element.source_location.json_path
            content = f'{path}: {base_text}' if path else base_text
            if not content.strip():
                continue

            parts = tokenizer.split_text(content, max_tokens=max_tokens, overlap_tokens=0)
            for part_index, part in enumerate(parts):
                location = location_to_dict(element.source_location)
                if len(parts) > 1:
                    location['json_part_index'] = part_index
                lineage = lineage_for_element(element)
                chunks.append(
                    ChunkDraft(
                        chunk_index=index,
                        content=part,
                        token_count=tokenizer.count_tokens(part),
                        element_type=element.kind,
                        source_location=location,
                        lineage=lineage,
                    )
                )
                index += 1
        return chunks, index
