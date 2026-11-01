from __future__ import annotations


class RagError(Exception):
    """Base RAG pipeline error."""


class RagRetrievalUnavailable(RagError):
    """Retrieval infrastructure unavailable — do not call the LLM."""

    def __init__(self, message: str, *, code: str = 'semantic_unavailable') -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = 503


class RagRetrievalConflict(RagError):
    """Embedding or activation conflict — do not call the LLM."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = 409


class RagRetrievalAccessDenied(RagError):
    def __init__(self, message: str, *, code: str = 'access_denied') -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = 403


class RagStructuredOutputError(RagError):
    """Invalid structured JSON from the LLM when RAG is enabled."""

    def __init__(self, message: str = 'Assistant returned an invalid structured response.') -> None:
        super().__init__(message)
        self.message = message
        self.code = 'invalid_structured_response'
        self.http_status = 502


class RagCitationError(RagError):
    """Answer missing required source citations."""

    def __init__(
        self,
        message: str = 'Assistant response must include source citations matching retrieved references.',
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = 'citation_required'
        self.http_status = 502
