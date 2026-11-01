from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db.models import QuerySet

from apps.authentication.models import User
from apps.document_chunking.constants import (
    VECTOR_DTYPE_FLOAT32,
    VECTOR_SERIALIZATION_VERSION,
    ChunkEmbeddingStatus,
    VectorKind,
)
from apps.document_chunking.models import ChunkEmbedding, DocumentChunk
from apps.documents.access import documents_for_user
from apps.model_management.models import BusinessModel
from apps.retrieval.constants import EMBEDDING_NORMALIZATION_POLICY, QDRANT_DISTANCE_METRIC
from apps.retrieval.exceptions import ActivationConsistencyError, EmbeddingCompatibilityError
from apps.retrieval.knowledge_authorization import document_ids_with_indexed_knowledge_access
from apps.vector_indexing.constants import IndexingActivationPhase, IndexingRunStatus
from apps.vector_indexing.models import DocumentIndexActivation, IndexingRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingConfigIdentity:
    embedding_model: str
    embedding_model_version: str
    embedding_dimension: int
    provider_name: str
    vector_kind: str
    dtype: str
    serialization_version: int
    normalization_policy: str
    distance_metric: str


@dataclass(frozen=True)
class DocumentActivationSnapshot:
    document_id: str
    active_artifact_version: int
    active_collection_name: str
    indexing_run_id: str


@dataclass(frozen=True)
class IndexingProfile:
    collection_name: str
    embedding: EmbeddingConfigIdentity
    document_ids: frozenset[str]
    activations_by_document: dict[str, DocumentActivationSnapshot]


def accessible_document_ids(*, user: User, business_model: BusinessModel) -> frozenset:
    ids = documents_for_user(user).filter(business_model=business_model).values_list('id', flat=True)
    return frozenset(str(doc_id) for doc_id in ids)


def _embedding_config_for_run(run: IndexingRun) -> EmbeddingConfigIdentity:
    rows = (
        ChunkEmbedding.objects.filter(
            document_chunk__chunking_run_id=run.chunking_run_id,
            vector_kind=VectorKind.SEMANTIC,
            status=ChunkEmbeddingStatus.SUCCEEDED,
        )
        .values(
            'provider_name',
            'dtype',
            'serialization_version',
            'embedding_model',
            'embedding_model_version',
            'embedding_dimension',
            'vector_kind',
        )
        .distinct()
    )
    distinct = list(rows)
    if len(distinct) != 1:
        raise ActivationConsistencyError(
            'Indexed embedding configuration for an active indexing run is ambiguous.'
        )
    row = distinct[0]
    if row['embedding_model'] != run.embedding_model or row['embedding_model_version'] != run.embedding_model_version:
        raise ActivationConsistencyError('Indexing run metadata does not match stored chunk embeddings.')
    if row['embedding_dimension'] != run.embedding_dimension:
        raise ActivationConsistencyError('Indexing run dimension does not match stored chunk embeddings.')
    return EmbeddingConfigIdentity(
        embedding_model=run.embedding_model,
        embedding_model_version=run.embedding_model_version,
        embedding_dimension=run.embedding_dimension,
        provider_name=row['provider_name'],
        vector_kind=row['vector_kind'],
        dtype=row['dtype'] or VECTOR_DTYPE_FLOAT32,
        serialization_version=int(row['serialization_version'] or VECTOR_SERIALIZATION_VERSION),
        normalization_policy=EMBEDDING_NORMALIZATION_POLICY,
        distance_metric=QDRANT_DISTANCE_METRIC,
    )


def _validate_activation_record(activation: DocumentIndexActivation) -> DocumentActivationSnapshot:
    doc_id = str(activation.document_id)
    if not activation.active_collection_name:
        raise ActivationConsistencyError(f'Document {doc_id} has no committed active collection.')

    if activation.pending_indexing_run_id is not None:
        logger.warning(
            'retrieval_activation_pending_present document_id=%s business_model_id=%s',
            doc_id,
            activation.business_model_id,
        )
        raise ActivationConsistencyError(f'Document {doc_id} has a pending index activation.')

    run = activation.active_indexing_run
    if run is None:
        raise ActivationConsistencyError(f'Document {doc_id} is missing an active indexing run.')

    if run.status != IndexingRunStatus.COMPLETED:
        raise ActivationConsistencyError(f'Document {doc_id} active indexing run is not completed.')
    if run.activation_phase != IndexingActivationPhase.COMMITTED:
        raise ActivationConsistencyError(f'Document {doc_id} active indexing run is not committed.')
    if not run.activation_reconciled:
        raise ActivationConsistencyError(f'Document {doc_id} active indexing run is not reconciled.')

    if run.artifact_version != activation.active_artifact_version:
        raise ActivationConsistencyError(f'Document {doc_id} artifact version mismatch.')
    if run.collection_name != activation.active_collection_name:
        raise ActivationConsistencyError(f'Document {doc_id} active collection mismatch.')
    if str(run.document_id) != doc_id:
        raise ActivationConsistencyError(f'Document {doc_id} activation document scope mismatch.')
    if run.business_model_id != activation.business_model_id:
        raise ActivationConsistencyError(f'Document {doc_id} activation business model mismatch.')

    if not run.embedding_model or not run.embedding_model_version or run.embedding_dimension <= 0:
        raise ActivationConsistencyError(f'Document {doc_id} has invalid embedding configuration metadata.')

    return DocumentActivationSnapshot(
        document_id=doc_id,
        active_artifact_version=activation.active_artifact_version,
        active_collection_name=activation.active_collection_name,
        indexing_run_id=str(run.id),
    )


def bulk_activation_snapshots(
    *,
    user: User,
    business_model: BusinessModel,
    document_ids: frozenset[str],
) -> dict[str, DocumentActivationSnapshot]:
    if not document_ids:
        return {}

    activations = (
        DocumentIndexActivation.objects.filter(
            document_id__in=document_ids,
            business_model=business_model,
        )
        .select_related('active_indexing_run', 'document')
    )

    snapshots: dict[str, DocumentActivationSnapshot] = {}
    for activation in activations:
        doc_id = str(activation.document_id)
        if doc_id not in document_ids:
            continue
        try:
            snapshots[doc_id] = _validate_activation_record(activation)
        except ActivationConsistencyError:
            raise
    return snapshots


def resolve_indexing_profile(
    *,
    user: User,
    business_model: BusinessModel,
    required_document_ids: frozenset[str] | None = None,
) -> IndexingProfile | None:
    owned = accessible_document_ids(user=user, business_model=business_model)
    if not owned:
        return None

    candidate_docs = owned
    if required_document_ids is not None:
        missing = required_document_ids - owned
        if missing:
            from apps.retrieval.exceptions import RetrievalAccessError

            raise RetrievalAccessError('One or more documents are not accessible to the current user.')
        candidate_docs = required_document_ids

    activations = (
        DocumentIndexActivation.objects.filter(
            document_id__in=candidate_docs,
            business_model=business_model,
        )
        .select_related('active_indexing_run')
    )

    validated_docs: dict[str, DocumentActivationSnapshot] = {}
    inconsistent_docs: list[str] = []

    for activation in activations:
        doc_id = str(activation.document_id)
        try:
            validated_docs[doc_id] = _validate_activation_record(activation)
        except ActivationConsistencyError:
            inconsistent_docs.append(doc_id)
            logger.warning(
                'retrieval_activation_inconsistent document_id=%s business_model=%s',
                doc_id,
                business_model.key,
            )

    if required_document_ids is not None:
        for doc_id in required_document_ids:
            if doc_id in inconsistent_docs or doc_id not in validated_docs:
                raise ActivationConsistencyError(
                    'One or more requested documents do not have a valid active index.'
                )

    retrievable_docs = document_ids_with_indexed_knowledge_access(
        user=user,
        business_model=business_model,
        document_ids=frozenset(validated_docs.keys()),
    )

    if required_document_ids is not None:
        if not retrievable_docs.issuperset(required_document_ids):
            raise ActivationConsistencyError(
                'One or more requested documents are not indexed in KnowledgeSource.'
            )

    eligible_docs = retrievable_docs
    if not eligible_docs:
        return None

    configs: dict[EmbeddingConfigIdentity, set[str]] = {}
    activations_by_document: dict[str, DocumentActivationSnapshot] = {}

    run_ids = {
        validated_docs[doc_id].indexing_run_id
        for doc_id in eligible_docs
        if doc_id in validated_docs
    }
    runs = {
        str(run.id): run
        for run in IndexingRun.objects.filter(id__in=run_ids).select_related('chunking_run')
    }

    for doc_id in eligible_docs:
        snapshot = validated_docs.get(doc_id)
        if snapshot is None:
            continue
        run = runs.get(snapshot.indexing_run_id)
        if run is None:
            raise ActivationConsistencyError('Active indexing run record is missing.')
        config = _embedding_config_for_run(run)
        configs.setdefault(config, set()).add(doc_id)
        activations_by_document[doc_id] = snapshot

    if not configs:
        return None

    if len(configs) > 1:
        summary = '; '.join(
            f'{cfg.embedding_model}/{cfg.embedding_model_version} '
            f'provider={cfg.provider_name} dim={cfg.embedding_dimension}'
            for cfg in configs.keys()
        )
        raise EmbeddingCompatibilityError(
            'Multiple incompatible indexed embedding configurations are active for this scope: '
            f'{summary}'
        )

    config, documents = next(iter(configs.items()))
    collection_name = next(iter(activations_by_document.values())).active_collection_name

    return IndexingProfile(
        collection_name=collection_name,
        embedding=config,
        document_ids=frozenset(documents),
        activations_by_document={doc_id: activations_by_document[doc_id] for doc_id in documents},
    )


def chunks_by_ids(*, chunk_ids: list, user: User, business_model: BusinessModel) -> QuerySet[DocumentChunk]:
    if not chunk_ids:
        return DocumentChunk.objects.none()
    return (
        DocumentChunk.objects.filter(
            id__in=chunk_ids,
            user=user,
            business_model=business_model,
        )
        .select_related('document', 'business_model')
        .only(
            'id',
            'document_id',
            'user_id',
            'business_model_id',
            'chunk_index',
            'content',
            'content_hash',
            'element_type',
            'source_type',
            'visibility',
            'document__original_filename',
            'document__user_id',
        )
    )
