from __future__ import annotations

from gateways.qdrant.client import QdrantGatewayClient


def get_qdrant_gateway() -> QdrantGatewayClient:
    return QdrantGatewayClient()
