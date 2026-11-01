'use client';

import { TrainingFileIcon } from '@/components/employee-space/TrainingFileIcon';
import { TrainingProgressBar } from '@/components/employee-space/TrainingProgressBar';
import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { getBusinessModelLabel } from '@/lib/dashboard/business-models';
import { formatFileSize } from '@/lib/employee-space/format';
import {
  formatTrainingStage,
  progressBarColorForJob,
} from '@/lib/employee-space/training-job-ui';
import type { UserTrainingDocument } from '@/lib/employee-space/types';
import { isActiveTrainingJobStatus } from '@/services/training-job-service';

type TrainingDocumentRowProps = {
  document: UserTrainingDocument;
};

export function TrainingDocumentRow({ document }: TrainingDocumentRowProps) {
  const job = document.trainingJob;
  const showProgress = Boolean(job);
  const updatedLabel = job
    ? `Job updated ${new Date(job.updatedAt).toLocaleString()}`
    : document.timeLabel;

  return (
    <li
      data-testid="training-document-row"
      data-document-id={document.id}
      data-status={document.status}
      data-job-status={job?.status ?? ''}
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
              {updatedLabel}
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
        <TrainingStatusBadge
          status={document.status}
          trainingJobStatus={job?.status ?? null}
        />
      </div>

      {showProgress && job ? (
        <div className="mt-3 space-y-2 border-t border-zinc-100 pt-3">
          <TrainingProgressBar
            percent={job.progress}
            barClassName={progressBarColorForJob(job.status)}
          />
          <p className="text-xs text-zinc-600" data-testid="document-training-stage">
            Stage:{' '}
            <span className="font-medium text-zinc-800">
              {formatTrainingStage(job.currentStage)}
            </span>
            {job.retryCount > 0 ? (
              <span className="text-orange-700"> · Retry {job.retryCount}</span>
            ) : null}
          </p>
          {job.dispatchError ? (
            <p className="text-xs text-amber-800" role="alert" data-testid="document-dispatch-error">
              {job.dispatchError}
            </p>
          ) : null}
        </div>
      ) : null}

      {!showProgress && document.status === 'processing' ? (
        <p className="mt-2 text-xs font-medium text-sky-800" data-testid="document-processing-hint">
          Processing…
        </p>
      ) : null}

      {!document.isStagedSelection &&
      (document.status === 'failed' ||
        job?.status === 'failed' ||
        document.failureReason) ? (
        <p className="mt-2 text-sm text-red-600" role="alert" data-testid="document-failure-reason">
          {document.failureReason ?? 'Training failed.'}
        </p>
      ) : null}

      {job && isActiveTrainingJobStatus(job.status) ? (
        <p className="mt-2 text-[11px] text-zinc-500" data-testid="document-training-active-hint">
          Training pipeline in progress (extraction through embedding). Vector index activation runs
          after the job completes.
        </p>
      ) : null}
    </li>
  );
}
