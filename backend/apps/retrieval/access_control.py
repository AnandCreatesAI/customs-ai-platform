from __future__ import annotations

import logging
import uuid

from apps.authentication.models import User
from apps.document_chunking.models import DocumentChunk
from apps.knowledge.models import KnowledgeVisibility
from apps.model_management.models import BusinessModel
from apps.retrieval.exceptions import RetrievalAccessError
from apps.retrieval.knowledge_authorization import chunk_passes_knowledge_visibility
from apps.retrieval.selectors import DocumentActivationSnapshot, accessible_document_ids

logger = logging.getLogger(__name__)


def validate_document_scope(
    *,
    user: User,
    business_model: BusinessModel,
    document_ids: list[str] | None,
) -> frozenset[str]:
    allowed = accessible_document_ids(user=user, business_model=business_model)
    if not document_ids:
        return allowed

    normalized: set[str] = set()
    for raw in document_ids:
        try:
            normalized.add(str(uuid.UUID(str(raw))))
        except ValueError as exc:
            raise RetrievalAccessError(f'Invalid document_id: {raw}') from exc

    disallowed = normalized - allowed
    if disallowed:
        raise RetrievalAccessError('One or more documents are not accessible to the current user.')
    return frozenset(normalized)


def authorize_chunk_hit(
    *,
    user: User,
    business_model: BusinessModel,
    chunk: DocumentChunk,
    payload: dict,
    business_model_key: str,
    activation: DocumentActivationSnapshot | None,
    knowledge_sources_for_chunk: list,
) -> bool:
    if chunk.user_id != user.id:
        logger.info('retrieval_hit_rejected reason=chunk_owner_mismatch')
        return False
    if chunk.business_model_id != business_model.id:
        logger.info('retrieval_hit_rejected reason=chunk_business_model_mismatch')
        return False
    if chunk.document.user_id != user.id:
        logger.info('retrieval_hit_rejected reason=document_owner_mismatch')
        return False

    if not payload_matches_chunk(
        payload=payload,
        chunk=chunk,
        business_model_key=business_model_key,
        activation=activation,
    ):
        logger.info('retrieval_hit_rejected reason=payload_mismatch')
        return False

    if not chunk_passes_knowledge_visibility(chunk=chunk, sources=knowledge_sources_for_chunk):
        logger.info('retrieval_hit_rejected reason=knowledge_visibility_conflict')
        return False

    return True


def payload_matches_chunk(
    *,
    payload: dict,
    chunk: DocumentChunk,
    business_model_key: str,
    activation: DocumentActivationSnapshot | None,
) -> bool:
    if str(payload.get('chunk_id')) != str(chunk.id):
        return False
    if str(payload.get('document_id')) != str(chunk.document_id):
        return False
    if str(payload.get('user_id')) != str(chunk.user_id):
        return False
    if payload.get('business_model_key') != business_model_key:
        return False
    if payload.get('is_active') is not True:
        return False
    payload_artifact = payload.get('artifact_version')
    if activation is not None and payload_artifact is not None:
        if int(payload_artifact) != int(activation.active_artifact_version):
            return False
    payload_hash = payload.get('content_hash')
    if payload_hash and payload_hash != chunk.content_hash:
        return False
    return True
