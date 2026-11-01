from __future__ import annotations

from apps.document_extraction.base import ExtractionContext
from apps.document_extraction.extractors.xlsx import XlsxExtractor
from apps.document_extraction.storage.temp_workspace import temporary_subdir
from apps.document_extraction.subprocess.libreoffice import convert_xls_to_xlsx


class XlsExtractor:
    key = 'xls'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('libreoffice')
        with temporary_subdir(ctx.workspace, prefix='lo-xls') as convert_dir:
            xlsx_path = convert_xls_to_xlsx(ctx.input_path, convert_dir)
            nested_ctx = ExtractionContext(
                document=ctx.document,
                input_path=xlsx_path,
                workspace=ctx.workspace,
                methods_used=ctx.methods_used,
            )
            elements = XlsxExtractor().extract(nested_ctx)
            ctx.methods_used[:] = nested_ctx.methods_used
            return elements
