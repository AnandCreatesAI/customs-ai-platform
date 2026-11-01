import type { EvidenceStatus, RagEvidenceDetail } from '@/types/rag-types';

export function evidenceStatusLabel(status: EvidenceStatus): string {
  switch (status) {
    case 'retrieval_backed':
      return 'Sources used';
    case 'partial_context':
      return 'Partial context';
    case 'no_matching_sources':
      return 'No matching sources';
    case 'no_indexed_corpus':
      return 'No indexed documents';
    default:
      return '';
  }
}

export function evidenceStatusHint(
  status: EvidenceStatus,
  detail?: RagEvidenceDetail,
): string | undefined {
  if (status === 'partial_context' && detail?.context_truncated) {
    return 'Retrieved context was truncated to fit model limits. The answer may not reflect all indexed passages.';
  }
  if (status === 'no_matching_sources') {
    return 'Indexed documents were searched but no matching passages were found for this question.';
  }
  if (status === 'no_indexed_corpus') {
    return 'No indexed documents are available for your account in this business model.';
  }
  if (status === 'retrieval_backed' && detail?.score_semantics) {
    return 'Similarity scores describe retrieval match, not answer correctness.';
  }
  return undefined;
}
