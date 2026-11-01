from __future__ import annotations

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_extraction.schema.types import Element
from apps.document_chunking.strategies._helpers import element_text, location_to_dict

_PROSE_KINDS = frozenset({'heading', 'paragraph', 'list_item'})


class ProseChunkStrategy:
    name = 'prose'

    def matches(self, profile: FormatProfile) -> bool:
        return True

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
            if element.kind in _PROSE_KINDS:
                selected.append(element)
                assigned.add(element.element_id)
            elif element.kind not in {
                'sheet',
                'sheet_row',
                'json_value',
                'field',
                'table',
                'table_row',
                'table_cell',
                'ocr_block',
                'vision_block',
                'image_ref',
            }:
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
        target = config.prose_target_tokens
        max_tokens = config.prose_max_tokens
        min_tokens = config.prose_min_tokens
        overlap = config.prose_overlap_tokens

        chunks: list[ChunkDraft] = []
        index = start_index
        section_title: str | None = None
        buffer_parts: list[str] = []
        buffer_elements: list[Element] = []
        buffer_location_key: tuple | None = None

        def location_key(element: Element) -> tuple:
            loc = element.source_location
            if loc is None:
                return ('none',)
            return (
                loc.page,
                loc.paragraph_index,
                loc.block_index,
                loc.sheet_name,
                loc.row_index,
                loc.json_path,
            )

        def flush_buffer() -> None:
            nonlocal buffer_location_key
            nonlocal index, buffer_parts, buffer_elements, section_title
            if not buffer_parts:
                return
            body = '\n\n'.join(buffer_parts)
            prefix = f'# {section_title}\n\n' if section_title else ''
            full_text = f'{prefix}{body}'.strip()
            buffer_parts = []
            elements_used = buffer_elements
            buffer_elements = []
            buffer_location_key = None
            if not full_text:
                return

            splits = tokenizer.split_text(
                full_text,
                max_tokens=max_tokens,
                overlap_tokens=overlap,
            )
            for part_index, part in enumerate(splits):
                primary = elements_used[0]
                location = location_to_dict(primary.source_location)
                if len(splits) > 1:
                    location['prose_part_index'] = part_index
                chunks.append(
                    ChunkDraft(
                        chunk_index=index,
                        content=part,
                        token_count=tokenizer.count_tokens(part),
                        element_type=primary.kind,
                        source_location=location,
                        lineage={
                            'element_ids': [el.element_id for el in elements_used],
                            'section_title': section_title,
                        },
                    )
                )
                index += 1

        for element in elements:
            if element.kind == 'heading':
                flush_buffer()
                section_title = element_text(element) or section_title
                continue
            text = element_text(element)
            if not text:
                continue
            element_location = location_key(element)
            if buffer_parts and buffer_location_key != element_location:
                flush_buffer()
            if not buffer_parts:
                buffer_location_key = element_location
            tentative = '\n\n'.join(buffer_parts + [text]) if buffer_parts else text
            tokens = tokenizer.count_tokens(
                f'# {section_title}\n\n{tentative}' if section_title else tentative
            )
            if buffer_parts and tokens > target:
                flush_buffer()
            buffer_parts.append(text)
            buffer_elements.append(element)

        flush_buffer()
        return chunks, index
