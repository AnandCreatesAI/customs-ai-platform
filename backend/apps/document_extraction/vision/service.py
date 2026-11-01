from __future__ import annotations

from apps.document_extraction.base import ExtractionContext, new_element_id
from apps.document_extraction.schema.types import Element
from apps.document_extraction.vision.policy import vision_allowed


def maybe_apply_vision(_ctx: ExtractionContext, elements: list[Element]) -> list[Element]:
    if not vision_allowed():
        return elements
    # Phase 3: explicit opt-in hook only; no automatic full-document vision calls.
    return elements
