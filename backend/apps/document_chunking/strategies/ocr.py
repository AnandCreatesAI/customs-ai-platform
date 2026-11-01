from __future__ import annotations

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_extraction.schema.types import Element
from apps.document_chunking.strategies._helpers import element_text, lineage_for_element, location_to_dict

_OCR_KINDS = frozenset({'ocr_block', 'vision_block'})


class OcrChunkStrategy:
    name = 'ocr'

    def matches(self, profile: FormatProfile) -> bool:
        return profile.has_ocr or profile.extractor_key == 'image'

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
            if element.kind in _OCR_KINDS:
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
        max_tokens = config.prose_max_tokens
        overlap = config.prose_overlap_tokens

        for element in elements:
            if element.kind not in _OCR_KINDS:
                continue
            content = element_text(element)
            if not content:
                continue
            parts = tokenizer.split_text(
                content,
                max_tokens=max_tokens,
                overlap_tokens=overlap,
            )
            for part_index, part in enumerate(parts):
                location = location_to_dict(element.source_location)
                if len(parts) > 1:
                    location['ocr_part_index'] = part_index
                chunks.append(
                    ChunkDraft(
                        chunk_index=index,
                        content=part,
                        token_count=tokenizer.count_tokens(part),
                        element_type=element.kind,
                        source_location=location,
                        lineage=lineage_for_element(element),
                    )
                )
                index += 1
        return chunks, index
