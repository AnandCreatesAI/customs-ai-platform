from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class QdrantPoint:
    point_id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(frozen=True)
class QdrantSearchHit:
    point_id: str
    score: float
    payload: dict[str, Any]


class QdrantGatewayProtocol(Protocol):
    def ensure_collection(self, *, collection_name: str, dimension: int) -> None:
        ...

    def upsert_points(self, *, collection_name: str, points: list[QdrantPoint]) -> None:
        ...

    def set_payload_by_filter(
        self,
        *,
        collection_name: str,
        payload: dict[str, Any],
        document_id: str,
        artifact_version: int,
    ) -> None:
        ...

    def health_check(self) -> bool:
        ...

    def search_points(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
        query_filter: Any | None = None,
        offset: int = 0,
    ) -> list[QdrantSearchHit]:
        ...
