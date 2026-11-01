from __future__ import annotations

from django.conf import settings

from gateways.qdrant.exceptions import QdrantConfigurationError


def require_qdrant_config() -> tuple[str, str]:
    if not settings.QDRANT_INDEXING_ENABLED:
        raise QdrantConfigurationError('Qdrant indexing is disabled.')
    url = (settings.QDRANT_URL or '').strip()
    api_key = (settings.QDRANT_API_KEY or '').strip()
    if not url:
        raise QdrantConfigurationError('QDRANT_URL is not configured.')
    if not api_key:
        raise QdrantConfigurationError('QDRANT_API_KEY is not configured.')
    return url, api_key


def collection_prefix() -> str:
    return (settings.QDRANT_COLLECTION_PREFIX or 'customs_ai').strip()


def resolve_collection_name(*, business_model_key: str, dimension: int) -> str:
    prefix = collection_prefix()
    safe_key = business_model_key.replace('-', '_').lower()
    return f'{prefix}_{safe_key}_v{dimension}'
