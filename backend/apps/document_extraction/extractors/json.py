from __future__ import annotations

import json
from typing import Any

from apps.document_extraction.base import ExtractionContext, ExtractionError, new_element_id
from apps.document_extraction.schema.types import Element, LocationRef


def _walk(value: Any, path: str, elements: list[Element]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            child_path = f'{path}.{key}' if path else f'$.{key}'
            _walk(nested, child_path, elements)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            child_path = f'{path}[{index}]'
            _walk(nested, child_path, elements)
    else:
        elements.append(
            Element(
                element_id=new_element_id(),
                kind='json_value',
                text=str(value),
                structured_data={'value': value, 'value_type': type(value).__name__},
                source_location=LocationRef(json_path=path),
                extraction_method='parsed',
            )
        )


class JsonExtractor:
    key = 'json'

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ctx.record_method('parsed')
        try:
            payload = json.loads(ctx.input_path.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExtractionError('Invalid JSON document.') from exc
        elements: list[Element] = []
        _walk(payload, '$', elements)
        return elements
