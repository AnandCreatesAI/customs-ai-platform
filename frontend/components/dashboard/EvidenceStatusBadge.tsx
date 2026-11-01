'use client';

import {
  evidenceStatusHint,
  evidenceStatusLabel,
} from '@/lib/dashboard/evidence-labels';
import type { EvidenceStatus, RagEvidenceDetail } from '@/types/rag-types';

type EvidenceStatusBadgeProps = {
  status: EvidenceStatus;
  detail?: RagEvidenceDetail;
};

export function EvidenceStatusBadge({ status, detail }: EvidenceStatusBadgeProps) {
  const label = evidenceStatusLabel(status);
  const hint = evidenceStatusHint(status, detail);
  if (!label) {
    return null;
  }

  return (
    <div
      data-testid="evidence-status-badge"
      className="mt-2 flex flex-col gap-0.5 text-xs text-zinc-500"
    >
      <span className="inline-flex w-fit items-center rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 font-medium text-zinc-600">
        {label}
      </span>
      {hint ? (
        <p data-testid="evidence-status-hint" className="max-w-prose leading-snug">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
