'use client';

import { TrainingFileIcon } from '@/components/employee-space/TrainingFileIcon';
import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { getBusinessModelLabel } from '@/lib/dashboard/business-models';
import { formatFileSize } from '@/lib/employee-space/format';
import type { UserTrainingDocument } from '@/lib/employee-space/types';

type TrainingDocumentRowProps = {
  document: UserTrainingDocument;
};

export function TrainingDocumentRow({ document }: TrainingDocumentRowProps) {
  return (
    <li
      data-testid="training-document-row"
      data-document-id={document.id}
      data-status={document.status}
      className="rounded-lg border border-zinc-200 bg-white p-3 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <TrainingFileIcon extension={document.extension} />
          <div className="min-w-0 flex-1">
            <p
              className="truncate text-sm font-semibold text-zinc-900"
              data-testid="document-filename"
            >
              {document.name}
            </p>
            <p className="text-xs text-zinc-500">
              <span data-testid="document-extension">{document.extension.toUpperCase()}</span>
              {' · '}
              <span data-testid="document-size">{formatFileSize(document.sizeBytes)}</span>
              {' · '}
              <span data-testid="document-model">{getBusinessModelLabel(document.modelKey)}</span>
            </p>
            <p className="mt-0.5 text-xs text-zinc-500" data-testid="document-time">
              {document.timeLabel}
            </p>
            {!document.isStagedSelection ? (
              <p className="mt-0.5 font-mono text-[10px] text-zinc-400" data-testid="document-id">
                {document.id}
              </p>
            ) : null}
            {document.isStagedSelection ? (
              <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-indigo-600">
                Selected — not uploaded yet
              </p>
            ) : null}
          </div>
        </div>
        <TrainingStatusBadge status={document.status} />
      </div>
      {document.status === 'processing' ? (
        <p className="mt-2 text-xs font-medium text-amber-800" data-testid="document-processing-hint">
          Processing…
        </p>
      ) : null}
      {document.status === 'failed' && document.failureReason ? (
        <p className="mt-2 text-sm text-red-600" role="alert" data-testid="document-failure-reason">
          {document.failureReason}
        </p>
      ) : null}
    </li>
  );
}
