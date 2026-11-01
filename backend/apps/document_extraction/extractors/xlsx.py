from __future__ import annotations

from openpyxl import load_workbook

from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.schema.types import Element, LocationRef


class XlsxExtractor:
    key = 'xlsx'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('openpyxl')
        try:
            workbook = load_workbook(filename=str(ctx.input_path), read_only=True, data_only=True)
        except Exception as exc:
            raise ExtractionError('Invalid or corrupt XLSX workbook.') from exc

        elements: list[Element] = []
        for sheet in workbook.worksheets:
            sheet_id = new_element_id()
            elements.append(
                Element(
                    element_id=sheet_id,
                    kind='sheet',
                    text=sheet.title,
                    source_location=LocationRef(sheet_name=sheet.title),
                    extraction_method='openpyxl',
                )
            )
            rows = sheet.iter_rows(values_only=True)
            try:
                header = next(rows)
            except StopIteration:
                continue
            headers = [
                str(cell).strip() if cell is not None else f'column_{index + 1}'
                for index, cell in enumerate(header)
            ]
            for row_index, row in enumerate(rows, start=2):
                if row is None or all(cell is None or str(cell).strip() == '' for cell in row):
                    continue
                structured: dict[str, str | None] = {}
                for col_index, header_name in enumerate(headers):
                    value = row[col_index] if col_index < len(row) else None
                    if value is None:
                        structured[header_name] = None
                    elif isinstance(value, (int, float)):
                        structured[header_name] = str(value)
                    else:
                        structured[header_name] = str(value)
                elements.append(
                    Element(
                        element_id=new_element_id(),
                        kind='sheet_row',
                        text=None,
                        structured_data=structured,
                        parent_element_id=sheet_id,
                        source_location=LocationRef(sheet_name=sheet.title, row_index=row_index),
                        extraction_method='openpyxl',
                    )
                )
        workbook.close()
        return elements
