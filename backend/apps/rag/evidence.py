from __future__ import annotations

from typing import Any

from apps.retrieval.constants import RetrievalStatus
from apps.retrieval.services import RetrievalServiceResult

from apps.rag.schemas import EvidenceDetail, EvidenceStatus, SourceReference


def sources_from_retrieval_context(context: dict[str, Any]) -> list[SourceReference]:
    raw_sources = context.get('sources') or []
    sources: list[SourceReference] = []
    for index, item in enumerate(raw_sources, start=1):
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get('chunk_id') or '').strip()
        document_id = str(item.get('document_id') or '').strip()
        if not chunk_id or not document_id:
            continue
        sources.append(
            SourceReference(
                ref=index,
                chunk_id=chunk_id,
                document_id=document_id,
                document_filename=str(item.get('document_filename') or '').strip(),
                chunk_index=int(item.get('chunk_index') or 0),
                score=float(item.get('score') or 0.0),
                artifact_version=int(item.get('artifact_version') or 0),
            ),
        )
    return sources


def evidence_detail_from_result(result: RetrievalServiceResult, *, chunk_count: int) -> EvidenceDetail:
    truncation = {}
    if isinstance(result.context, dict):
        truncation = result.context.get('truncation') or {}
    context_truncated = bool(truncation)
    return EvidenceDetail(
        retrieval_status=str(result.status),
        chunk_count=chunk_count,
        context_truncated=context_truncated,
        score_semantics=result.score_semantics or '',
        truncation=truncation if isinstance(truncation, dict) else {},
    )


def evidence_status_for_chunks(
    *,
    retrieval_status: str,
    chunk_count: int,
    context_truncated: bool,
) -> EvidenceStatus:
    if retrieval_status == RetrievalStatus.NO_INDEXED_CONTENT:
        return EvidenceStatus.NO_INDEXED_CORPUS
    if chunk_count <= 0:
        return EvidenceStatus.NO_MATCHING_SOURCES
    if context_truncated:
        return EvidenceStatus.PARTIAL_CONTEXT
    return EvidenceStatus.RETRIEVAL_BACKED


def classify_retrieval_result(result: RetrievalServiceResult) -> tuple[EvidenceStatus, EvidenceDetail, list[SourceReference]]:
    sources = sources_from_retrieval_context(result.context if isinstance(result.context, dict) else {})
    chunk_count = len(sources)
    detail = evidence_detail_from_result(result, chunk_count=chunk_count)
    status = evidence_status_for_chunks(
        retrieval_status=str(result.status),
        chunk_count=chunk_count,
        context_truncated=detail.context_truncated,
    )
    return status, detail, sources
