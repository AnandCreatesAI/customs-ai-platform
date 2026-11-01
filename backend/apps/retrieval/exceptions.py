from __future__ import annotations


class RetrievalError(Exception):
    def __init__(self, message: str, *, code: str = 'retrieval_error') -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class RetrievalValidationError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code='validation_error')


class SemanticRetrievalUnavailableError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code='semantic_unavailable')


class EmbeddingCompatibilityError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code='embedding_incompatible')


class RetrievalAccessError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code='access_denied')


class ActivationConsistencyError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code='activation_inconsistent')
