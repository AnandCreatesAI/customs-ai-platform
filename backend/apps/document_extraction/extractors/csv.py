from __future__ import annotations

import csv

from charset_normalizer import from_bytes

from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.schema.types import Element, LocationRef


class CsvExtractor:
    key = 'csv'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('parsed')
        raw = ctx.input_path.read_bytes()
        detected = from_bytes(raw).best()
        text = str(detected) if detected is not None else raw.decode('utf-8', errors='replace')
        try:
            sample = text[:2048]
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(text.splitlines(), dialect=dialect)
        if not reader.fieldnames:
            raise ExtractionError('CSV file is missing a header row.')
        elements: list[Element] = []
        for row_index, row in enumerate(reader, start=2):
            structured = {key: (value if value != '' else None) for key, value in row.items()}
            elements.append(
                Element(
                    element_id=new_element_id(),
                    kind='sheet_row',
                    text=None,
                    structured_data=structured,
                    source_location=LocationRef(sheet_name='csv', row_index=row_index),
                    extraction_method='parsed',
                )
            )
        return elements
