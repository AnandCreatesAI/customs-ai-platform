from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.authentication.models import User
from apps.documents.business_model_access import get_active_business_model
from apps.model_management.models import BusinessModel
from apps.retrieval.exceptions import RetrievalValidationError
from model_handlers.registry import MODEL_HANDLER_CLASSES


@dataclass(frozen=True)
class ProcessedQuery:
    user: User
    business_model: BusinessModel
    query_text: str
    top_k: int
    min_score: float | None


def process_retrieval_query(
    *,
    user: User,
    business_model_key: str,
    query_text: str,
    top_k: int | None,
    min_score: float | None,
) -> ProcessedQuery:
    if user is None or not getattr(user, 'is_authenticated', False):
        raise RetrievalValidationError('Authentication is required.')
    if not user.is_active:
        raise RetrievalValidationError('User account is inactive.')

    normalized = (query_text or '').strip()
    if not normalized:
        raise RetrievalValidationError('Query must be a non-empty string.')
    max_len = settings.RETRIEVAL_MAX_QUERY_LENGTH
    if len(normalized) > max_len:
        raise RetrievalValidationError(f'Query exceeds maximum length of {max_len} characters.')

    key = (business_model_key or '').strip()
    if key not in MODEL_HANDLER_CLASSES:
        raise RetrievalValidationError('Unsupported business model.')

    try:
        business_model = get_active_business_model(key)
    except ValidationError as exc:
        detail = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        raise RetrievalValidationError(str(detail)) from exc

    resolved_top_k = top_k if top_k is not None else settings.RETRIEVAL_DEFAULT_TOP_K
    if resolved_top_k < settings.RETRIEVAL_MIN_TOP_K or resolved_top_k > settings.RETRIEVAL_MAX_TOP_K:
        raise RetrievalValidationError(
            f'top_k must be between {settings.RETRIEVAL_MIN_TOP_K} and {settings.RETRIEVAL_MAX_TOP_K}.'
        )

    resolved_min_score = min_score
    if resolved_min_score is None:
        resolved_min_score = settings.RETRIEVAL_DEFAULT_MIN_SCORE
    if resolved_min_score is not None:
        if resolved_min_score < 0.0 or resolved_min_score > 1.0:
            raise RetrievalValidationError('min_score must be between 0.0 and 1.0.')

    return ProcessedQuery(
        user=user,
        business_model=business_model,
        query_text=normalized,
        top_k=resolved_top_k,
        min_score=resolved_min_score,
    )
