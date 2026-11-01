from gateways.qdrant.factory import get_qdrant_gateway


def check_qdrant_health() -> bool:
    return get_qdrant_gateway().health_check()
