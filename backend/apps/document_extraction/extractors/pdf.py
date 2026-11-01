from __future__ import annotations

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.conf import pdf_native_min_chars_per_page
from apps.document_extraction.ocr.engine import run_ocr_on_image
from apps.document_extraction.ocr.pdf_render import render_pdf_page
from apps.document_extraction.schema.types import Element, LocationRef

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None


class PdfExtractor:
    key = 'pdf'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('pypdf')
        elements: list[Element] = []
        ocr_pages: set[int] = set()
        try:
            reader = PdfReader(str(ctx.input_path))
        except PdfReadError as exc:
            raise ExtractionError('PDF is corrupt or unreadable.') from exc
        if reader.is_encrypted:
            raise ExtractionError('Encrypted PDFs are not supported.')

        page_text_lengths: dict[int, int] = {}
        for page_index, page in enumerate(reader.pages):
            text = (page.extract_text() or '').strip()
            page_text_lengths[page_index] = len(text)
            if len(text) >= pdf_native_min_chars_per_page():
                elements.append(
                    Element(
                        element_id=new_element_id(),
                        kind='paragraph',
                        text=text,
                        source_location=LocationRef(page=page_index + 1, block_index=0),
                        extraction_method='pypdf',
                    )
                )
            elif self._page_likely_scanned(text, page_index, reader):
                ocr_pages.add(page_index)

        if pdfplumber is not None:
            ctx.record_method('pdfplumber')
            elements.extend(self._extract_tables(ctx, ocr_pages))

        for page_index in sorted(ocr_pages):
            ctx.record_method('ocr')
            image_path = render_pdf_page(ctx.input_path, page_index)
            blocks = run_ocr_on_image(image_path)
            if not blocks:
                continue
            combined = ' '.join(block.text for block in blocks)
            avg_conf = None
            scores = [b.confidence for b in blocks if b.confidence is not None]
            if scores:
                avg_conf = sum(scores) / len(scores)
            elements.append(
                Element(
                    element_id=new_element_id(),
                    kind='ocr_block',
                    text=combined,
                    source_location=LocationRef(page=page_index + 1),
                    extraction_method='ocr',
                    confidence=avg_conf,
                )
            )
        if not elements:
            raise ExtractionError('PDF contains no extractable text.')
        return elements

    def _page_likely_scanned(self, native_text: str, page_index: int, reader: PdfReader) -> bool:
        if len(native_text.strip()) >= pdf_native_min_chars_per_page():
            return False
        if len(native_text.strip()) > 0:
            return False
        try:
            page = reader.pages[page_index]
            if '/XObject' in page.get('/Resources', {}):
                return True
        except Exception:
            return True
        return True

    def _extract_tables(self, ctx: ExtractionContext, ocr_pages: set[int]) -> list[Element]:
        tables: list[Element] = []
        with pdfplumber.open(str(ctx.input_path)) as pdf:
            for page_index, page in enumerate(pdf.pages):
                if page_index in ocr_pages:
                    continue
                for table_index, table in enumerate(page.extract_tables() or []):
                    if not table:
                        continue
                    table_id = new_element_id()
                    tables.append(
                        Element(
                            element_id=table_id,
                            kind='table',
                            text=None,
                            structured_data={'rows': len(table)},
                            source_location=LocationRef(page=page_index + 1, block_index=table_index),
                            extraction_method='pdfplumber',
                        )
                    )
                    for row_index, row in enumerate(table):
                        cells = [str(cell or '').strip() for cell in row]
                        tables.append(
                            Element(
                                element_id=new_element_id(),
                                kind='table_row',
                                text=' | '.join(c for c in cells if c),
                                structured_data={'cells': cells},
                                parent_element_id=table_id,
                                source_location=LocationRef(
                                    page=page_index + 1,
                                    row_index=row_index,
                                ),
                                extraction_method='pdfplumber',
                            )
                        )
        return tables
