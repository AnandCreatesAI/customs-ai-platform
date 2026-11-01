class QdrantGatewayError(Exception):
    pass


class QdrantConfigurationError(QdrantGatewayError):
    pass


class QdrantAuthError(QdrantGatewayError):
    pass


class QdrantUnavailableError(QdrantGatewayError):
    pass


class QdrantValidationError(QdrantGatewayError):
    pass


class QdrantCollectionMismatchError(QdrantValidationError):
    pass
