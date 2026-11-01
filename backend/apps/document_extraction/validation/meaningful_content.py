from __future__ import annotations

import re

from apps.document_extraction.schema.types import Element

_MEANINGFUL = re.compile(r'[\w\d]', re.UNICODE)


def has_meaningful_content(elements: list[Element]) -> bool:
    for element in elements:
        for candidate in (element.normalized_text, element.text):
            if candidate and _MEANINGFUL.search(candidate):
                return True
        if element.structured_data:
            for value in element.structured_data.values():
                if value is not None and str(value).strip():
                    return True
    return False
