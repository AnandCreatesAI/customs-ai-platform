from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from django.conf import settings

from apps.document_chunking.constants import VectorKind
from apps.retrieval.access_control import authorize_chunk_hit, validate_document_scope
from apps.retrieval.constants import RetrievalStatus
from apps.retrieval.context_builder import RetrievalContext, build_retrieval_context
from apps.retrieval.exceptions import (
    EmbeddingCompatibilityError,
    RetrievalError,
    SemanticRetrievalUnavailableError,
)
from apps.retrieval.filters import build_qdrant_search_filter
from apps.retrieval.knowledge_authorization import knowledge_sources_by_document
from apps.retrieval.query_embedding import QueryEmbeddingResult, embed_query_text
from apps.retrieval.query_processor import ProcessedQuery
from apps.retrieval.ranking import RankedHit, rank_and_deduplicate_hits
from apps.retrieval.selectors import EmbeddingConfigIdentity, IndexingProfile, chunks_by_ids, resolve_indexing_profile
from gateways.qdrant.exceptions import QdrantConfigurationError, QdrantGatewayError
from gateways.qdrant.factory import get_qdrant_gateway

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalResultItem:
    chunk_id: str
    document_id: str
    score: float
    chunk_index: int
    content: str
    element_type: str
    source_type: str
    artifact_version: int
    content_hash: str
    truncated: bool = False


@dataclass(frozen=True)
class RetrievalServiceResult:
    status: str
    business_model_key: str
    query: str
    top_k: int
    min_score: float | None
    embedding: dict
    results: list[RetrievalResultItem]
    context: dict
    message: str = ''
    score_semantics: str = ''


def _validate_query_embedding_compatibility(
    *,
    query_embedding: QueryEmbeddingResult,
    profile_embedding: EmbeddingConfigIdentity,
) -> None:
    if query_embedding.vector_kind != VectorKind.SEMANTIC:
        raise SemanticRetrievalUnavailableError('Query embedding is not semantic.')
    pairs = (
        ('embedding_dimension', query_embedding.embedding_dimension, profile_embedding.embedding_dimension),
        ('embedding_model', query_embedding.embedding_model, profile_embedding.embedding_model),
        ('embedding_model_version', query_embedding.embedding_model_version, profile_embedding.embedding_model_version),
        ('provider_name', query_embedding.provider_name, profile_embedding.provider_name),
        ('dtype', query_embedding.dtype, profile_embedding.dtype),
        ('serialization_version', query_embedding.serialization_version, profile_embedding.serialization_version),
        ('normalization_policy', query_embedding.normalization_policy, profile_embedding.normalization_policy),
        ('distance_metric', query_embedding.distance_metric, profile_embedding.distance_metric),
    )
    for field_name, query_value, indexed_value in pairs:
        if query_value != indexed_value:
            raise EmbeddingCompatibilityError(
                f'Query/index embedding mismatch for {field_name}: '
                f'query={query_value!r} indexed={indexed_value!r}.'
            )


def _search_validated_hits(
    *,
    gateway,
    profile: IndexingProfile,
    query_vector: list[float],
    processed: ProcessedQuery,
    search_documents: frozenset[str],
    knowledge_by_document: dict,
) -> list[RankedHit]:
    batch_size = processed.top_k * settings.RETRIEVAL_OVERFETCH_MULTIPLIER
    max_batches = settings.RETRIEVAL_SEARCH_MAX_BATCHES
    query_filter = build_qdrant_search_filter(
        business_model_key=processed.business_model.key,
        user_id=str(processed.user.id),
        document_ids=search_documents,
    )

    verified: list[RankedHit] = []
    seen_chunk_ids: set[str] = set()
    offset = 0

    for _batch in range(max_batches):
        if len(verified) >= processed.top_k:
            break
        try:
            raw_hits = gateway.search_points(
                collection_name=profile.collection_name,
                vector=query_vector,
                limit=batch_size,
                query_filter=query_filter,
                offset=offset,
            )
        except QdrantGatewayError:
            raise

        if not raw_hits:
            break

        offset += len(raw_hits)
        preliminary: list[RankedHit] = []
        for hit in raw_hits:
            chunk_id = str(hit.payload.get('chunk_id') or hit.point_id)
            if chunk_id in seen_chunk_ids:
                continue
            preliminary.append(
                RankedHit(
                    chunk_id=chunk_id,
                    document_id=str(hit.payload.get('document_id') or ''),
                    score=hit.score,
                    payload=hit.payload,
                )
            )

        ranked = rank_and_deduplicate_hits(
            preliminary,
            min_score=processed.min_score,
            top_k=batch_size,
        )
        if not ranked:
            continue

        chunk_ids = [hit.chunk_id for hit in ranked]
        chunk_qs = chunks_by_ids(
            chunk_ids=chunk_ids,
            user=processed.user,
            business_model=processed.business_model,
        )
        chunks_by_id = {str(chunk.id): chunk for chunk in chunk_qs}

        for hit in ranked:
            if len(verified) >= processed.top_k:
                break
            if hit.chunk_id in seen_chunk_ids:
                continue
            chunk = chunks_by_id.get(hit.chunk_id)
            if chunk is None:
                continue
            doc_id = str(chunk.document_id)
            activation = profile.activations_by_document.get(doc_id)
            sources = knowledge_by_document.get(doc_id, [])
            if not authorize_chunk_hit(
                user=processed.user,
                business_model=processed.business_model,
                chunk=chunk,
                payload=hit.payload,
                business_model_key=processed.business_model.key,
                activation=activation,
                knowledge_sources_for_chunk=sources,
            ):
                continue
            seen_chunk_ids.add(hit.chunk_id)
            verified.append(hit)

    return verified[: processed.top_k]


def retrieve_semantic(*, processed: ProcessedQuery, document_ids: list[str] | None = None) -> RetrievalServiceResult:
    if not settings.RETRIEVAL_ENABLED:
        raise RetrievalError('Semantic retrieval is disabled.', code='retrieval_disabled')
    if not settings.QDRANT_INDEXING_ENABLED:
        raise SemanticRetrievalUnavailableError('Vector indexing is disabled; retrieval is unavailable.')

    scope_documents = validate_document_scope(
        user=processed.user,
        business_model=processed.business_model,
        document_ids=document_ids,
    )
    required = frozenset(scope_documents) if document_ids is not None else None

    profile = resolve_indexing_profile(
        user=processed.user,
        business_model=processed.business_model,
        required_document_ids=required,
    )
    if profile is None:
        return RetrievalServiceResult(
            status=RetrievalStatus.NO_INDEXED_CONTENT,
            business_model_key=processed.business_model.key,
            query=processed.query_text,
            top_k=processed.top_k,
            min_score=processed.min_score,
            embedding={},
            results=[],
            context={'chunks': [], 'sources': [], 'truncation': {}},
            message='No active vector index found for accessible documents.',
            score_semantics=settings.RETRIEVAL_SCORE_SEMANTICS,
        )

    search_documents = scope_documents & profile.document_ids
    if not search_documents:
        return RetrievalServiceResult(
            status=RetrievalStatus.NO_INDEXED_CONTENT,
            business_model_key=processed.business_model.key,
            query=processed.query_text,
            top_k=processed.top_k,
            min_score=processed.min_score,
            embedding={},
            results=[],
            context={'chunks': [], 'sources': [], 'truncation': {}},
            message='No indexed documents match the requested scope.',
            score_semantics=settings.RETRIEVAL_SCORE_SEMANTICS,
        )

    query_embedding = embed_query_text(query_text=processed.query_text)
    _validate_query_embedding_compatibility(
        query_embedding=query_embedding,
        profile_embedding=profile.embedding,
    )

    knowledge_by_document = knowledge_sources_by_document(
        document_ids=search_documents,
        business_model=processed.business_model,
    )

    try:
        gateway = get_qdrant_gateway()
        verified = _search_validated_hits(
            gateway=gateway,
            profile=profile,
            query_vector=query_embedding.vector,
            processed=processed,
            search_documents=search_documents,
            knowledge_by_document=knowledge_by_document,
        )
    except QdrantConfigurationError as exc:
        logger.warning('retrieval_qdrant_configuration_error error=%s', exc.__class__.__name__)
        raise SemanticRetrievalUnavailableError('Vector store is not configured for retrieval.') from exc
    except QdrantGatewayError as exc:
        logger.warning('retrieval_qdrant_unavailable error=%s', exc.__class__.__name__)
        raise RetrievalError('Vector search is temporarily unavailable.', code='qdrant_error') from exc

    chunk_ids = [hit.chunk_id for hit in verified]
    chunks_by_id = {
        str(chunk.id): chunk
        for chunk in chunks_by_ids(
            chunk_ids=chunk_ids,
            user=processed.user,
            business_model=processed.business_model,
        )
    }

    context: RetrievalContext = build_retrieval_context(ranked=verified, chunks_by_id=chunks_by_id)
    chunks_by_id_map = {chunk.chunk_id: chunk for chunk in context.chunks}

    results = [
        RetrievalResultItem(
            chunk_id=source.chunk_id,
            document_id=source.document_id,
            score=source.score,
            chunk_index=source.chunk_index,
            content=chunks_by_id_map[source.chunk_id].content,
            element_type=chunks_by_id_map[source.chunk_id].element_type,
            source_type=chunks_by_id_map[source.chunk_id].source_type,
            artifact_version=source.artifact_version,
            content_hash=source.content_hash,
            truncated=chunks_by_id_map[source.chunk_id].truncated,
        )
        for source in context.sources
    ]

    embedding_meta = {
        'embedding_model': query_embedding.embedding_model,
        'embedding_model_version': query_embedding.embedding_model_version,
        'embedding_dimension': query_embedding.embedding_dimension,
        'vector_kind': query_embedding.vector_kind,
        'provider_name': query_embedding.provider_name,
        'dtype': query_embedding.dtype,
        'serialization_version': query_embedding.serialization_version,
        'normalization_policy': query_embedding.normalization_policy,
        'distance_metric': query_embedding.distance_metric,
        'collection_name': profile.collection_name,
    }

    return RetrievalServiceResult(
        status=RetrievalStatus.OK,
        business_model_key=processed.business_model.key,
        query=processed.query_text,
        top_k=processed.top_k,
        min_score=processed.min_score,
        embedding=embedding_meta,
        results=results,
        context={
            'chunks': [asdict(chunk) for chunk in context.chunks],
            'sources': [asdict(source) for source in context.sources],
            'truncation': context.truncation,
        },
        score_semantics=settings.RETRIEVAL_SCORE_SEMANTICS,
    )
