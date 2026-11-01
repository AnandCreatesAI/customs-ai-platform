from __future__ import annotations

from apps.rag.schemas import EvidenceStatus

NO_INDEXED_CORPUS_ANSWER = (
    'I do not have any indexed documents available for your account in this business model. '
    'Upload and index relevant materials, then ask your question again.'
)

NO_MATCHING_SOURCES_ANSWER = (
    'I searched your indexed documents but did not find passages that match this question. '
    'Try rephrasing your question or add more relevant source material.'
)


def deterministic_no_sources_answer(evidence_status: EvidenceStatus) -> str:
    if evidence_status == EvidenceStatus.NO_INDEXED_CORPUS:
        return NO_INDEXED_CORPUS_ANSWER
    return NO_MATCHING_SOURCES_ANSWER
