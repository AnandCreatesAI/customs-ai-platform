from __future__ import annotations

import logging

from django.db.models import Q

from apps.authentication.models import User
from apps.knowledge.models import (
    KnowledgeIndexingStatus,
    KnowledgeSource,
    KnowledgeSourceType,
    KnowledgeVisibility,
)
from apps.model_management.models import BusinessModel

logger = logging.getLogger(__name__)


def bulk_knowledge_sources_for_documents(*, document_ids: frozenset, business_model: BusinessModel):
    if not document_ids:
        return KnowledgeSource.objects.none()
    return (
        KnowledgeSource.objects.filter(business_model=business_model)
        .filter(
            Q(document_links__document_id__in=document_ids)
            | Q(
                document_id__in=document_ids,
                source_type=KnowledgeSourceType.DOCUMENT,
            )
        )
        .prefetch_related('document_links')
        .distinct()
    )


def document_ids_with_indexed_knowledge_access(
    *,
    user: User,
    business_model: BusinessModel,
    document_ids: frozenset[str],
) -> frozenset[str]:
    """
    Documents retrievable under owner-only policy with INDEXED KnowledgeSource lifecycle.

    Shared cross-user access is not supported (Phase 5 policy).
    """
    if not document_ids:
        return frozenset()

    allowed: set[str] = set()
    sources = bulk_knowledge_sources_for_documents(
        document_ids=document_ids,
        business_model=business_model,
    )

    links_by_document: dict[str, set] = {}
    for source in sources:
        if source.indexing_status != KnowledgeIndexingStatus.INDEXED:
            continue
        if source.visibility == KnowledgeVisibility.PRIVATE and source.user_id != user.id:
            continue
        if source.visibility == KnowledgeVisibility.SHARED and source.user_id != user.id:
            continue

        linked_doc_ids: set[str] = set()
        for link in source.document_links.all():
            linked_doc_ids.add(str(link.document_id))
        if source.document_id and source.source_type == KnowledgeSourceType.DOCUMENT:
            linked_doc_ids.add(str(source.document_id))

        for doc_id in linked_doc_ids:
            if doc_id not in document_ids:
                continue
            links_by_document.setdefault(doc_id, set()).add(source.id)
            allowed.add(doc_id)

    return frozenset(allowed)


def knowledge_sources_by_document(
    *,
    document_ids: frozenset[str],
    business_model: BusinessModel,
) -> dict[str, list[KnowledgeSource]]:
    mapping: dict[str, list[KnowledgeSource]] = {doc_id: [] for doc_id in document_ids}
    for source in bulk_knowledge_sources_for_documents(document_ids=document_ids, business_model=business_model):
        linked: set[str] = set()
        for link in source.document_links.all():
            linked.add(str(link.document_id))
        if source.document_id and source.source_type == KnowledgeSourceType.DOCUMENT:
            linked.add(str(source.document_id))
        for doc_id in linked:
            if doc_id in mapping:
                mapping[doc_id].append(source)
    return mapping


def chunk_passes_knowledge_visibility(*, chunk, sources: list[KnowledgeSource]) -> bool:
    if not sources:
        return False
    indexed_sources = [s for s in sources if s.indexing_status == KnowledgeIndexingStatus.INDEXED]
    if not indexed_sources:
        return False

    has_shared = any(s.visibility == KnowledgeVisibility.SHARED for s in indexed_sources)
    has_private = any(s.visibility == KnowledgeVisibility.PRIVATE for s in indexed_sources)

    if chunk.visibility == KnowledgeVisibility.PRIVATE:
        if has_shared:
            return False
        return has_private

    if chunk.visibility == KnowledgeVisibility.SHARED:
        if has_private and not has_shared:
            return False
        return has_shared

    return False
