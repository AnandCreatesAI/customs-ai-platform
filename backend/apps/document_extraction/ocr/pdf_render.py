from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium


def render_pdf_page(pdf_path: Path, page_index: int, dpi: int = 200) -> Path:
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[page_index]
        scale = dpi / 72.0
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        out = pdf_path.parent / f'page_{page_index + 1}_ocr.png'
        pil_image.save(out, format='PNG')
        return out
    finally:
        pdf.close()
