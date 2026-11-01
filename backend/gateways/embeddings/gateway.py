from __future__ import annotations

from gateways.embeddings.interfaces import EmbeddingProvider, EmbeddingProviderError, EmbeddingRequest


class EmbeddingGateway:
    def __init__(self, provider: EmbeddingProvider) -> None:
        if provider is None:
            raise ValueError('Embedding provider is required')
        self._provider = provider

    @property
    def provider(self) -> EmbeddingProvider:
        return self._provider

    def embed_texts(self, request: EmbeddingRequest):
        if not request.texts:
            raise ValueError('Embedding request must include at least one text.')
        try:
            return self._provider.embed(request)
        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(
                f'Embedding failed via provider {self._provider.provider_name!r}'
            ) from exc
