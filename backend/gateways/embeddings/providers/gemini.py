from __future__ import annotations

import os
import time

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from apps.document_chunking.constants import VectorKind
from gateways.embeddings.interfaces import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingVector,
)


class GeminiEmbeddingProvider(EmbeddingProvider):
    provider_name = 'gemini'
    vector_kind = VectorKind.SEMANTIC

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get('GEMINI_API_KEY', '')
        if not resolved_key.strip():
            raise EmbeddingProviderError('GEMINI_API_KEY is not configured')

        self.model_name = (model or settings.GEMINI_EMBEDDING_MODEL).strip()
        self.model_version = self.model_name
        self.default_dimension = dimension or settings.GEMINI_EMBEDDING_DIMENSION
        self._client = client
        self._api_key = resolved_key

    def _get_client(self) -> genai.Client:
        if self._client is None:
            timeout_ms = settings.EMBEDDING_TIMEOUT_SECONDS * 1000
            http_options = genai_types.HttpOptions(timeout=timeout_ms)
            self._client = genai.Client(api_key=self._api_key, http_options=http_options)
        return self._client

    def max_input_tokens(self) -> int:
        return min(
            settings.GEMINI_EMBEDDING_MAX_INPUT_TOKENS,
            settings.EMBEDDING_MAX_INPUT_TOKENS,
        )

    def max_batch_size(self) -> int:
        return settings.EMBEDDING_BATCH_SIZE

    def _embed_single(self, text: str) -> list[float]:
        client = self._get_client()
        config = genai_types.EmbedContentConfig(
            output_dimensionality=self.default_dimension,
        )
        last_error: Exception | None = None
        for attempt in range(settings.EMBEDDING_MAX_RETRIES + 1):
            try:
                response = client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                    config=config,
                )
                values = response.embeddings[0].values
                if values is None:
                    raise EmbeddingProviderError('Gemini returned empty embedding values.')
                if len(values) != self.default_dimension:
                    raise EmbeddingProviderError(
                        f'Gemini dimension mismatch: expected {self.default_dimension}, '
                        f'got {len(values)}.'
                    )
                return list(values)
            except genai_errors.APIError as exc:
                last_error = exc
                if attempt >= settings.EMBEDDING_MAX_RETRIES:
                    break
                time.sleep(min(2**attempt, 8))
            except Exception as exc:
                raise EmbeddingProviderError(f'Gemini embedding failed: {exc}') from exc
        raise EmbeddingProviderError(f'Gemini embedding failed after retries: {last_error}')

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        if not request.texts:
            return EmbeddingResponse(
                vectors=[],
                provider_name=self.provider_name,
                model_name=self.model_name,
                model_version=self.model_version,
                dimension=self.default_dimension,
            )

        vectors: list[EmbeddingVector] = []
        batch_size = self.max_batch_size()
        for offset in range(0, len(request.texts), batch_size):
            batch = request.texts[offset : offset + batch_size]
            for text in batch:
                if not text or not text.strip():
                    raise EmbeddingProviderError('Cannot embed empty chunk content.')
                values = self._embed_single(text)
                vectors.append(
                    EmbeddingVector(values=values, vector_kind=self.vector_kind)
                )

        return EmbeddingResponse(
            vectors=vectors,
            provider_name=self.provider_name,
            model_name=self.model_name,
            model_version=self.model_version,
            dimension=self.default_dimension,
        )
