from __future__ import annotations

import zipfile
from pathlib import Path

from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph

from apps.document_extraction.base import ExtractionContext, new_element_id
from apps.document_extraction.schema.types import Element, LocationRef


def _iter_block_items(document: DocxDocument):
    parent_elm = document.element.body
    for child in parent_elm.iterchildren():
        tag = child.tag.split('}')[-1]
        if tag == 'p':
            yield Paragraph(child, document)
        elif tag == 'tbl':
            yield Table(child, document)


class DocxExtractor:
    key = 'docx'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('python_docx')
        document = DocxDocument(str(ctx.input_path))
        elements: list[Element] = []
        block_index = 0
        for block in _iter_block_items(document):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                if not text:
                    continue
                style = (block.style.name if block.style is not None else '').lower()
                kind = 'heading' if 'heading' in style else 'paragraph'
                elements.append(
                    Element(
                        element_id=new_element_id(),
                        kind=kind,
                        text=text,
                        source_location=LocationRef(paragraph_index=block_index, block_index=block_index),
                        extraction_method='python_docx',
                    )
                )
                block_index += 1
            elif isinstance(block, Table):
                table_id = new_element_id()
                elements.append(
                    Element(
                        element_id=table_id,
                        kind='table',
                        text=None,
                        structured_data={'rows': len(block.rows), 'cols': len(block.columns)},
                        source_location=LocationRef(block_index=block_index),
                        extraction_method='python_docx',
                    )
                )
                for row_index, row in enumerate(block.rows):
                    cells = [cell.text.strip() for cell in row.cells]
                    elements.append(
                        Element(
                            element_id=new_element_id(),
                            kind='table_row',
                            text=' | '.join(c for c in cells if c),
                            structured_data={'cells': cells},
                            parent_element_id=table_id,
                            source_location=LocationRef(block_index=block_index, row_index=row_index),
                            extraction_method='python_docx',
                        )
                    )
                block_index += 1

        elements.extend(self._embedded_images(ctx))
        return elements

    def _embedded_images(self, ctx: ExtractionContext) -> list[Element]:
        refs: list[Element] = []
        media_dir = ctx.workspace / 'docx_media'
        media_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(ctx.input_path) as archive:
                for name in archive.namelist():
                    if not name.startswith('word/media/'):
                        continue
                    data = archive.read(name)
                    if len(data) > 10 * 1024 * 1024:
                        continue
                    out = media_dir / Path(name).name
                    out.write_bytes(data)
                    refs.append(
                        Element(
                            element_id=new_element_id(),
                            kind='image_ref',
                            text=None,
                            structured_data={'media_path': str(out), 'archive_path': name},
                            extraction_method='python_docx',
                        )
                    )
        except zipfile.BadZipFile:
            return refs
        return refs
