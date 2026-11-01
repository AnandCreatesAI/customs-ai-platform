from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmbeddingRequest:
    texts: list[str]


@dataclass(frozen=True)
class EmbeddingVector:
    values: list[float]
    vector_kind: str


@dataclass(frozen=True)
class EmbeddingResponse:
    vectors: list[EmbeddingVector]
    provider_name: str
    model_name: str
    model_version: str
    dimension: int


class EmbeddingProviderError(Exception):
    pass


class EmbeddingProvider:
    provider_name: str
    model_name: str
    model_version: str
    vector_kind: str
    default_dimension: int

    def max_input_tokens(self) -> int:
        raise NotImplementedError

    def max_batch_size(self) -> int:
        raise NotImplementedError

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        raise NotImplementedError
