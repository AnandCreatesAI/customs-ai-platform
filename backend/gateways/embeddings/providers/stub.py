from __future__ import annotations

import hashlib
import struct

from django.conf import settings

from apps.document_chunking.constants import VectorKind
from gateways.embeddings.interfaces import (
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingVector,
)


class StubEmbeddingProvider(EmbeddingProvider):
    provider_name = 'stub'
    model_name = 'stub'
    model_version = '1'
    vector_kind = VectorKind.STUB_NON_SEMANTIC

    def __init__(self, *, dimension: int | None = None) -> None:
        self.default_dimension = dimension or settings.GEMINI_EMBEDDING_DIMENSION

    def max_input_tokens(self) -> int:
        return settings.CHUNKING_PROSE_MAX_TOKENS

    def max_batch_size(self) -> int:
        return settings.EMBEDDING_BATCH_SIZE

    def _vector_for_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode('utf-8')).digest()
        values: list[float] = []
        while len(values) < self.default_dimension:
            block = hashlib.sha256(digest + struct.pack('<I', len(values))).digest()
            for index in range(0, len(block), 4):
                if len(values) >= self.default_dimension:
                    break
                chunk = block[index : index + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b'\0')
                unsigned = struct.unpack('<I', chunk)[0]
                values.append((unsigned / 2**32) * 2.0 - 1.0)
        return values

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        vectors = [
            EmbeddingVector(
                values=self._vector_for_text(text),
                vector_kind=self.vector_kind,
            )
            for text in request.texts
        ]
        return EmbeddingResponse(
            vectors=vectors,
            provider_name=self.provider_name,
            model_name=self.model_name,
            model_version=self.model_version,
            dimension=self.default_dimension,
        )
