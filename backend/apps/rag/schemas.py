from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EvidenceStatus(StrEnum):
    RETRIEVAL_BACKED = 'retrieval_backed'
    PARTIAL_CONTEXT = 'partial_context'
    NO_MATCHING_SOURCES = 'no_matching_sources'
    NO_INDEXED_CORPUS = 'no_indexed_corpus'


@dataclass(frozen=True)
class SourceReference:
    ref: int
    chunk_id: str
    document_id: str
    document_filename: str
    chunk_index: int
    score: float
    artifact_version: int

    def to_api_dict(self) -> dict[str, Any]:
        return {
            'ref': self.ref,
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'document_filename': self.document_filename,
            'chunk_index': self.chunk_index,
            'score': self.score,
            'artifact_version': self.artifact_version,
        }

    def to_metadata_dict(self) -> dict[str, Any]:
        return self.to_api_dict()


@dataclass(frozen=True)
class EvidenceDetail:
    retrieval_status: str
    chunk_count: int
    context_truncated: bool
    score_semantics: str
    truncation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'retrieval_status': self.retrieval_status,
            'chunk_count': self.chunk_count,
            'context_truncated': self.context_truncated,
            'score_semantics': self.score_semantics,
            'truncation': self.truncation,
        }


@dataclass(frozen=True)
class RagRetrievalMeta:
    top_k: int
    min_score: float | None
    embedding_model: str
    collection_name: str

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            'top_k': self.top_k,
            'min_score': self.min_score,
            'embedding_model': self.embedding_model,
            'collection_name': self.collection_name,
        }


@dataclass(frozen=True)
class RagGroundedContext:
    """Authorized retrieval outcome ready for prompt formatting."""

    sources: list[SourceReference]
    reference_blocks: str
    evidence_status: EvidenceStatus
    evidence_detail: EvidenceDetail
    retrieval_meta: RagRetrievalMeta


@dataclass(frozen=True)
class RagNoSourcesOutcome:
    answer: str
    evidence_status: EvidenceStatus
    evidence_detail: EvidenceDetail
    sources: list[SourceReference] = field(default_factory=list)
    retrieval_meta: RagRetrievalMeta | None = None


@dataclass(frozen=True)
class RagAssistantPayload:
    answer: str
    sources: list[SourceReference]
    evidence_status: EvidenceStatus
    evidence_detail: EvidenceDetail
    retrieval_meta: RagRetrievalMeta | None
    suggested_questions: list[str]
    conversation_title: str | None
