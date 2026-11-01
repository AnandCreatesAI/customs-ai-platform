from __future__ import annotations

from django.conf import settings

from gateways.embeddings.gateway import EmbeddingGateway
from gateways.embeddings.interfaces import EmbeddingProvider, EmbeddingProviderError
from gateways.embeddings.providers.gemini import GeminiEmbeddingProvider
from gateways.embeddings.providers.stub import StubEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    provider_key = settings.EMBEDDING_PROVIDER.strip().lower()
    if provider_key == 'stub':
        return StubEmbeddingProvider()
    if provider_key == 'gemini':
        if not settings.EMBEDDING_ALLOW_EXTERNAL:
            raise EmbeddingProviderError(
                'Gemini embedding is disabled. Set EMBEDDING_ALLOW_EXTERNAL=true '
                'after explicit authorization for external processing.'
            )
        return GeminiEmbeddingProvider()
    raise EmbeddingProviderError(f'Unknown embedding provider: {provider_key}')


def get_embedding_gateway() -> EmbeddingGateway:
    return EmbeddingGateway(get_embedding_provider())
