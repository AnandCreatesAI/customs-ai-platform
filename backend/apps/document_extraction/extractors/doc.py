from __future__ import annotations

from apps.document_extraction.base import ExtractionContext
from apps.document_extraction.schema.types import Element
from apps.document_extraction.extractors.docx import DocxExtractor
from apps.document_extraction.storage.temp_workspace import temporary_subdir
from apps.document_extraction.subprocess.libreoffice import convert_doc_to_docx


class DocExtractor:
    key = 'doc'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('libreoffice')
        with temporary_subdir(ctx.workspace, prefix='lo-doc') as convert_dir:
            docx_path = convert_doc_to_docx(ctx.input_path, convert_dir)
            nested_ctx = ExtractionContext(
                document=ctx.document,
                input_path=docx_path,
                workspace=ctx.workspace,
                methods_used=ctx.methods_used,
            )
            elements = DocxExtractor().extract(nested_ctx)
            ctx.methods_used[:] = nested_ctx.methods_used
            return elements
