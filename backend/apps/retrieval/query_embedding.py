from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.document_chunking.constants import (
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
    VectorKind,
)
from apps.retrieval.constants import EMBEDDING_NORMALIZATION_POLICY, QDRANT_DISTANCE_METRIC
from apps.retrieval.exceptions import SemanticRetrievalUnavailableError
from gateways.embeddings.factory import get_embedding_gateway
from gateways.embeddings.interfaces import EmbeddingProviderError, EmbeddingRequest


@dataclass(frozen=True)
class QueryEmbeddingResult:
    vector: list[float]
    embedding_model: str
    embedding_model_version: str
    embedding_dimension: int
    vector_kind: str
    provider_name: str
    dtype: str
    serialization_version: int
    normalization_policy: str
    distance_metric: str


def embed_query_text(*, query_text: str) -> QueryEmbeddingResult:
    if settings.EMBEDDING_PROVIDER.strip().lower() == 'stub':
        raise SemanticRetrievalUnavailableError(
            'Semantic retrieval is unavailable while EMBEDDING_PROVIDER=stub. '
            'Configure a semantic embedding provider (e.g. gemini with EMBEDDING_ALLOW_EXTERNAL=true).'
        )

    gateway = get_embedding_gateway()
    provider = gateway.provider
    if provider.vector_kind != VectorKind.SEMANTIC:
        raise SemanticRetrievalUnavailableError(
            'Semantic retrieval requires a semantic embedding provider; '
            f'configured provider {provider.provider_name!r} is not semantic.'
        )

    try:
        response = gateway.embed_texts(EmbeddingRequest(texts=[query_text]))
    except EmbeddingProviderError as exc:
        raise SemanticRetrievalUnavailableError('Query embedding failed.') from exc

    if not response.vectors:
        raise SemanticRetrievalUnavailableError('Query embedding returned no vectors.')

    vector = response.vectors[0]
    if vector.vector_kind != VectorKind.SEMANTIC:
        raise SemanticRetrievalUnavailableError(
            'Query embedding is not semantic; cannot perform vector search.'
        )

    dimension = response.dimension
    if len(vector.values) != dimension:
        raise SemanticRetrievalUnavailableError(
            'Query vector dimension does not match expected embedding dimension.'
        )

    if not all(isinstance(v, (int, float)) for v in vector.values):
        raise SemanticRetrievalUnavailableError('Query vector contains non-numeric values.')

    return QueryEmbeddingResult(
        vector=list(vector.values),
        embedding_model=response.model_name,
        embedding_model_version=response.model_version,
        embedding_dimension=dimension,
        vector_kind=vector.vector_kind,
        provider_name=response.provider_name,
        dtype=VECTOR_DTYPE_FLOAT32,
        serialization_version=VECTOR_SERIALIZATION_VERSION,
        normalization_policy=EMBEDDING_NORMALIZATION_POLICY,
        distance_metric=QDRANT_DISTANCE_METRIC,
    )
