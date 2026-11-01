from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from gateways.qdrant.config import require_qdrant_config
from gateways.qdrant.exceptions import (
    QdrantAuthError,
    QdrantCollectionMismatchError,
    QdrantUnavailableError,
    QdrantValidationError,
)
from gateways.qdrant.interfaces import QdrantPoint, QdrantSearchHit

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        url, api_key = require_qdrant_config()
        _client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=settings.QDRANT_TIMEOUT_SECONDS,
        )
    return _client


def reset_client_for_tests() -> None:
    global _client
    _client = None


def _call_with_retries(func):
    last_exc: Exception | None = None
    for attempt in range(settings.QDRANT_MAX_RETRIES + 1):
        try:
            return func()
        except (QdrantCollectionMismatchError, QdrantValidationError):
            raise
        except Exception as exc:
            last_exc = exc
            message = str(exc).lower()
            if 'unauthorized' in message or 'forbidden' in message or '401' in message:
                raise QdrantAuthError('Qdrant authentication failed.') from exc
            if 'dimension' in message or 'validation' in message:
                raise QdrantValidationError(str(exc)) from exc
            if attempt >= settings.QDRANT_MAX_RETRIES:
                break
            time.sleep(settings.QDRANT_RETRY_BACKOFF_SECONDS * (2**attempt))
    raise QdrantUnavailableError('Qdrant request failed after retries.') from last_exc


class QdrantGatewayClient:
    def ensure_collection(self, *, collection_name: str, dimension: int) -> None:
        client = get_qdrant_client()

        def _ensure() -> None:
            exists = client.collection_exists(collection_name)
            if not exists:
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=dimension,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                return
            info = client.get_collection(collection_name)
            params = info.config.params.vectors
            if isinstance(params, qmodels.VectorParams):
                existing_size = params.size
                existing_distance = params.distance
            else:
                raise QdrantCollectionMismatchError(
                    'Collection uses named vectors; Phase 5 expects a single vector config.'
                )
            if existing_size != dimension:
                raise QdrantCollectionMismatchError(
                    f'Collection {collection_name!r} dimension {existing_size} '
                    f'does not match required dimension {dimension}.'
                )
            if existing_distance != qmodels.Distance.COSINE:
                raise QdrantCollectionMismatchError(
                    f'Collection {collection_name!r} distance {existing_distance!r} is not COSINE.'
                )

        _call_with_retries(_ensure)

    def upsert_points(self, *, collection_name: str, points: list[QdrantPoint]) -> None:
        if not points:
            return
        client = get_qdrant_client()

        def _upsert() -> None:
            client.upsert(
                collection_name=collection_name,
                points=[
                    qmodels.PointStruct(id=point.point_id, vector=point.vector, payload=point.payload)
                    for point in points
                ],
                wait=True,
            )

        _call_with_retries(_upsert)

    def set_payload_by_filter(
        self,
        *,
        collection_name: str,
        payload: dict[str, Any],
        document_id: str,
        artifact_version: int,
    ) -> None:
        client = get_qdrant_client()
        filter_ = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key='document_id',
                    match=qmodels.MatchValue(value=document_id),
                ),
                qmodels.FieldCondition(
                    key='artifact_version',
                    match=qmodels.MatchValue(value=artifact_version),
                ),
            ]
        )

        def _set_payload() -> None:
            client.set_payload(
                collection_name=collection_name,
                payload=payload,
                points=filter_,
                wait=True,
            )

        _call_with_retries(_set_payload)

    def search_points(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
        query_filter: qmodels.Filter | None = None,
        offset: int = 0,
    ) -> list[QdrantSearchHit]:
        if limit <= 0:
            return []
        client = get_qdrant_client()

        def _search() -> list[QdrantSearchHit]:
            response = client.query_points(
                collection_name=collection_name,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                offset=max(0, offset),
                with_payload=True,
            )
            hits: list[QdrantSearchHit] = []
            for point in response.points:
                payload = dict(point.payload or {})
                hits.append(
                    QdrantSearchHit(
                        point_id=str(point.id),
                        score=float(point.score or 0.0),
                        payload=payload,
                    )
                )
            return hits

        return _call_with_retries(_search)

    def health_check(self) -> bool:
        try:
            client = get_qdrant_client()
            _call_with_retries(lambda: client.get_collections())
            return True
        except Exception:
            logger.warning('qdrant_health_check_failed', exc_info=True)
            return False
