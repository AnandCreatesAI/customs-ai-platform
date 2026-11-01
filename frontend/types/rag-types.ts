export type EvidenceStatus =
  | 'retrieval_backed'
  | 'partial_context'
  | 'no_matching_sources'
  | 'no_indexed_corpus';

export type RagSourceReference = {
  ref: number;
  chunk_id: string;
  document_id: string;
  document_filename: string;
  chunk_index: number;
  score: number;
  artifact_version: number;
};

export type RagEvidenceDetail = {
  retrieval_status: string;
  chunk_count: number;
  context_truncated: boolean;
  score_semantics: string;
  truncation: Record<string, unknown>;
};

export type AssistantRagMetadata = {
  sources: RagSourceReference[];
  evidenceStatus?: EvidenceStatus;
  evidenceDetail?: RagEvidenceDetail;
};

const EVIDENCE_STATUSES: EvidenceStatus[] = [
  'retrieval_backed',
  'partial_context',
  'no_matching_sources',
  'no_indexed_corpus',
];

export function isEvidenceStatus(value: string): value is EvidenceStatus {
  return (EVIDENCE_STATUSES as string[]).includes(value);
}

export function parseRagSource(value: unknown): RagSourceReference | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const record = value as Record<string, unknown>;
  const ref = record.ref;
  const chunkId = record.chunk_id;
  const documentId = record.document_id;
  if (typeof ref !== 'number' || !Number.isFinite(ref)) {
    return null;
  }
  if (typeof chunkId !== 'string' || !chunkId.trim()) {
    return null;
  }
  if (typeof documentId !== 'string' || !documentId.trim()) {
    return null;
  }
  return {
    ref,
    chunk_id: chunkId,
    document_id: documentId,
    document_filename:
      typeof record.document_filename === 'string' ? record.document_filename : '',
    chunk_index: typeof record.chunk_index === 'number' ? record.chunk_index : 0,
    score: typeof record.score === 'number' ? record.score : 0,
    artifact_version:
      typeof record.artifact_version === 'number' ? record.artifact_version : 0,
  };
}

export function parseRagSources(value: unknown): RagSourceReference[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const byRef = new Map<number, RagSourceReference>();
  for (const item of value) {
    const parsed = parseRagSource(item);
    if (parsed && !byRef.has(parsed.ref)) {
      byRef.set(parsed.ref, parsed);
    }
  }
  return [...byRef.values()].sort((a, b) => a.ref - b.ref);
}

export function parseRagEvidenceDetail(value: unknown): RagEvidenceDetail | undefined {
  if (typeof value !== 'object' || value === null) {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const truncation = record.truncation;
  return {
    retrieval_status:
      typeof record.retrieval_status === 'string' ? record.retrieval_status : '',
    chunk_count: typeof record.chunk_count === 'number' ? record.chunk_count : 0,
    context_truncated: Boolean(record.context_truncated),
    score_semantics:
      typeof record.score_semantics === 'string' ? record.score_semantics : '',
    truncation:
      typeof truncation === 'object' && truncation !== null && !Array.isArray(truncation)
        ? (truncation as Record<string, unknown>)
        : {},
  };
}

export function parseAssistantRagFromRecord(
  record: Record<string, unknown>,
): AssistantRagMetadata {
  const sources = parseRagSources(record.sources);
  const statusRaw = record.evidence_status;
  const evidenceStatus =
    typeof statusRaw === 'string' && isEvidenceStatus(statusRaw) ? statusRaw : undefined;
  const evidenceDetail = parseRagEvidenceDetail(record.evidence_detail);
  return { sources, evidenceStatus, evidenceDetail };
}

export function sourcesByRef(sources: RagSourceReference[]): Map<number, RagSourceReference> {
  const map = new Map<number, RagSourceReference>();
  for (const source of sources) {
    if (!map.has(source.ref)) {
      map.set(source.ref, source);
    }
  }
  return map;
}

export function displayFilename(source: RagSourceReference): string {
  const name = source.document_filename.trim();
  if (name) {
    return name.replace(/[\u0000-\u001f<>]/g, '');
  }
  return `Document ${source.document_id.slice(0, 8)}…`;
}
