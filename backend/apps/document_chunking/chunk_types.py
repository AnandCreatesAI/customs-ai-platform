from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


@dataclass
class ChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    element_type: str
    source_location: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return compute_content_hash(self.content)
