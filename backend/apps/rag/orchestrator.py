from __future__ import annotations

import logging

from django.conf import settings

from apps.authentication.models import User
from apps.retrieval.constants import RetrievalStatus
from apps.retrieval.exceptions import (
    ActivationConsistencyError,
    EmbeddingCompatibilityError,
    RetrievalAccessError,
    RetrievalError,
    RetrievalValidationError,
    SemanticRetrievalUnavailableError,
)
from apps.retrieval.query_processor import process_retrieval_query
from apps.retrieval.services import RetrievalServiceResult, retrieve_semantic

from apps.rag.context_formatter import chunks_text_by_ref_from_context, format_reference_blocks
from apps.rag.evidence import classify_retrieval_result
from apps.rag.exceptions import (
    RagRetrievalAccessDenied,
    RagRetrievalConflict,
    RagRetrievalUnavailable,
)
from apps.rag.messages import deterministic_no_sources_answer
from apps.rag.schemas import (
    EvidenceStatus,
    RagGroundedContext,
    RagNoSourcesOutcome,
    RagRetrievalMeta,
)

logger = logging.getLogger(__name__)


def run_rag_retrieval(
    *,
    user: User,
    business_model_key: str,
    query_text: str,
) -> RagGroundedContext | RagNoSourcesOutcome:
    """
    Run Phase 6 retrieval in-process. Returns grounded context or a no-sources outcome.
    Raises RagRetrieval* on infrastructure / conflict errors (no LLM).

    Callers must pass the authoritative business model key (e.g. conversation.business_model.key).
    When RAG is enabled, retrieval infrastructure failures always propagate; there is no
    ungrounded LLM fallback.
    """
    try:
        processed = process_retrieval_query(
            user=user,
            business_model_key=business_model_key,
            query_text=query_text,
            top_k=settings.RAG_CHAT_TOP_K,
            min_score=settings.RAG_CHAT_MIN_SCORE,
        )
        result = retrieve_semantic(processed=processed, document_ids=None)
    except RetrievalValidationError as exc:
        raise RagRetrievalUnavailable(str(exc.message), code=exc.code) from exc
    except SemanticRetrievalUnavailableError as exc:
        raise RagRetrievalUnavailable(str(exc.message), code=exc.code) from exc
    except EmbeddingCompatibilityError as exc:
        raise RagRetrievalConflict(str(exc.message), code=exc.code) from exc
    except ActivationConsistencyError as exc:
        raise RagRetrievalConflict(str(exc.message), code=exc.code) from exc
    except RetrievalAccessError as exc:
        raise RagRetrievalAccessDenied(str(exc.message), code=exc.code) from exc
    except RetrievalError as exc:
        if exc.code in ('qdrant_error', 'retrieval_disabled'):
            raise RagRetrievalUnavailable(str(exc.message), code=exc.code) from exc
        raise RagRetrievalUnavailable(str(exc.message), code=exc.code) from exc

    return _classify_result(result)


def _classify_result(result: RetrievalServiceResult) -> RagGroundedContext | RagNoSourcesOutcome:
    evidence_status, evidence_detail, sources = classify_retrieval_result(result)

    retrieval_meta = _retrieval_meta_from_result(result)

    if evidence_status in (EvidenceStatus.NO_INDEXED_CORPUS, EvidenceStatus.NO_MATCHING_SOURCES):
        logger.info(
            'rag_no_sources status=%s chunk_count=%s',
            result.status,
            evidence_detail.chunk_count,
        )
        return RagNoSourcesOutcome(
            answer=deterministic_no_sources_answer(evidence_status),
            evidence_status=evidence_status,
            evidence_detail=evidence_detail,
            sources=[],
            retrieval_meta=retrieval_meta,
        )

    context_dict = result.context if isinstance(result.context, dict) else {}
    chunks_by_ref = chunks_text_by_ref_from_context(context_dict)
    reference_blocks = format_reference_blocks(sources=sources, chunks_by_ref=chunks_by_ref)

    logger.info(
        'rag_grounded status=%s chunk_count=%s truncated=%s',
        result.status,
        len(sources),
        evidence_detail.context_truncated,
    )

    return RagGroundedContext(
        sources=sources,
        reference_blocks=reference_blocks,
        evidence_status=evidence_status,
        evidence_detail=evidence_detail,
        retrieval_meta=retrieval_meta,
    )


def _retrieval_meta_from_result(result: RetrievalServiceResult) -> RagRetrievalMeta:
    embedding = result.embedding if isinstance(result.embedding, dict) else {}
    return RagRetrievalMeta(
        top_k=result.top_k,
        min_score=result.min_score,
        embedding_model=str(embedding.get('embedding_model') or ''),
        collection_name=str(embedding.get('collection_name') or ''),
    )
