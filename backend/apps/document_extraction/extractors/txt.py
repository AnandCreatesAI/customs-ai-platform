from __future__ import annotations

from charset_normalizer import from_bytes

from apps.document_extraction.base import ExtractionContext, new_element_id
from apps.document_extraction.schema.types import Element, LocationRef


class TxtExtractor:
    key = 'txt'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('parsed')
        raw = ctx.input_path.read_bytes()
        detected = from_bytes(raw).best()
        text = str(detected) if detected is not None else raw.decode('utf-8', errors='replace')
        elements: list[Element] = []
        for index, paragraph in enumerate(text.split('\n\n')):
            cleaned = paragraph.strip()
            if not cleaned:
                continue
            elements.append(
                Element(
                    element_id=new_element_id(),
                    kind='paragraph',
                    text=cleaned,
                    source_location=LocationRef(paragraph_index=index),
                    extraction_method='parsed',
                )
            )
        return elements
