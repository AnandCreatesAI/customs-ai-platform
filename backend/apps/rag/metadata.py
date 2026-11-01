from __future__ import annotations

from typing import Any

from apps.rag.schemas import EvidenceDetail, EvidenceStatus, RagRetrievalMeta, SourceReference


def build_rag_message_metadata(
    *,
    suggested_questions: list[str],
    sources: list[SourceReference],
    evidence_status: EvidenceStatus | str,
    evidence_detail: EvidenceDetail,
    retrieval_meta: RagRetrievalMeta | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        'suggested_questions': suggested_questions[:3],
        'sources': [source.to_metadata_dict() for source in sources],
        'evidence_status': str(evidence_status),
        'evidence_detail': evidence_detail.to_dict(),
    }
    if retrieval_meta is not None:
        metadata['rag_retrieval'] = retrieval_meta.to_metadata_dict()
    return metadata
