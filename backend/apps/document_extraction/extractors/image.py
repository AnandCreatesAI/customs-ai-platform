from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.ocr.engine import run_ocr_on_image
from apps.document_extraction.schema.types import Element, LocationRef


class ImageExtractor:
    key = 'image'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('ocr')
        try:
            with Image.open(ctx.input_path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ExtractionError('Unsupported or corrupt image file.') from exc

        ref_id = new_element_id()
        elements = [
            Element(
                element_id=ref_id,
                kind='image_ref',
                text=None,
                structured_data={'path': str(ctx.input_path)},
                extraction_method='parsed',
            )
        ]
        blocks = run_ocr_on_image(Path(ctx.input_path))
        if not blocks:
            raise ExtractionError('OCR produced no text for image.')
        for block_index, block in enumerate(blocks):
            elements.append(
                Element(
                    element_id=new_element_id(),
                    kind='ocr_block',
                    text=block.text,
                    parent_element_id=ref_id,
                    source_location=LocationRef(block_index=block_index, bbox=block.bbox),
                    extraction_method='ocr',
                    confidence=block.confidence,
                )
            )
        return elements
