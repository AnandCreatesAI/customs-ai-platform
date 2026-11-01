from __future__ import annotations

from typing import Any

from apps.document_extraction.schema.types import Element, LocationRef


def location_to_dict(location: LocationRef | None) -> dict[str, Any]:
    if location is None:
        return {}
    payload = {
        'page': location.page,
        'bbox': location.bbox,
        'sheet_name': location.sheet_name,
        'row_index': location.row_index,
        'column_index': location.column_index,
        'json_path': location.json_path,
        'paragraph_index': location.paragraph_index,
        'block_index': location.block_index,
    }
    return {key: value for key, value in payload.items() if value is not None}


def lineage_for_element(element: Element) -> dict[str, Any]:
    payload: dict[str, Any] = {'element_ids': [element.element_id]}
    if element.parent_element_id:
        payload['parent_element_id'] = element.parent_element_id
    return payload


def element_text(element: Element) -> str:
    return (element.normalized_text or element.text or '').strip()
