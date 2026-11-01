from __future__ import annotations

import re
import unicodedata

from apps.document_extraction.schema.types import Element

_MULTI_SPACE = re.compile(r'[ \t]+')
_MULTI_NL = re.compile(r'\n{3,}')


def normalize_text_value(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = unicodedata.normalize('NFKC', text)
    normalized = normalized.replace('\r\n', '\n').replace('\r', '\n')
    normalized = _MULTI_SPACE.sub(' ', normalized)
    normalized = _MULTI_NL.sub('\n\n', normalized)
    return normalized.strip()


def normalize_elements(elements: list[Element]) -> list[Element]:
    for element in elements:
        element.normalized_text = normalize_text_value(element.text)
    return elements
