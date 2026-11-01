from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from apps.documents.models import Document
from apps.document_extraction.schema.types import Element


@dataclass
class ExtractionContext:
    document: Document
    input_path: Path
    workspace: Path
    methods_used: list[str] = field(default_factory=list)

    def record_method(self, method: str) -> None:
        if method not in self.methods_used:
            self.methods_used.append(method)


class ExtractionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DocumentExtractor(Protocol):
    key: str

    def extract(self, ctx: ExtractionContext) -> list[Element]:
        ...


def new_element_id() -> str:
    return uuid.uuid4().hex
