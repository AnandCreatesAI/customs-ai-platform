'use client';

import { useMemo, useState } from 'react';

import { RecentTrainingActivity } from '@/components/employee-space/RecentTrainingActivity';
import { TrainingDocumentRow } from '@/components/employee-space/TrainingDocumentRow';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import type {
  DocumentDisplayStatus,
  RecentDocumentActivity,
  TrainingFileMetadata,
  UserTrainingDocument,
} from '@/lib/employee-space/types';
import { USER_DATA_ISOLATION_NOTICE } from '@/lib/employee-space/user-scoped-data';

export type DocumentStatusFilter = DocumentDisplayStatus | 'all' | 'selected';

type MyDocumentsPanelProps = {
  userId: number;
  documents: UserTrainingDocument[];
  documentsLoading: boolean;
  documentsError: string | null;
  trainingJobsError?: string | null;
  onRetryTrainingJobs?: () => void;
  onRetryLoad: () => void;
  hasMoreDocuments: boolean;
  onLoadMore: () => void;
  loadingMore: boolean;
  stagedFiles: TrainingFileMetadata[];
  stagedFileGroupTitle: string | null;
  stagedTextLabel: string | null;
  stagedTextModelKey: BusinessModelKey | null;
  stagedJsonLabel: string | null;
  stagedJsonModelKey: BusinessModelKey | null;
  recentActivity: RecentDocumentActivity[];
};

function stagedFileToDocument(
  file: TrainingFileMetadata,
  ownerUserId: number,
  groupTitle: string | null,
): UserTrainingDocument {
  const timeLabel = groupTitle
    ? `Selected · ${groupTitle} · not uploaded`
    : 'Selected · not uploaded';
  return {
    id: `staged-${file.id}`,
    ownerUserId,
    name: file.name,
    extension: file.extension,
    sizeBytes: file.sizeBytes,
    modelKey: file.modelKey,
    status: 'pending',
    timeLabel,
    sourceType: 'file',
    isDemo: false,
    isStagedSelection: true,
  };
}

export function MyDocumentsPanel({
  userId,
  documents,
  documentsLoading,
  documentsError,
  trainingJobsError = null,
  onRetryTrainingJobs,
  onRetryLoad,
  hasMoreDocuments,
  onLoadMore,
  loadingMore,
  stagedFiles,
  stagedFileGroupTitle,
  stagedTextLabel,
  stagedTextModelKey,
  stagedJsonLabel,
  stagedJsonModelKey,
  recentActivity,
}: MyDocumentsPanelProps) {
  const [statusFilter, setStatusFilter] = useState<DocumentStatusFilter>('all');

  const stagedDocuments = useMemo(() => {
    const fromFiles = stagedFiles.map((file) =>
      stagedFileToDocument(file, userId, stagedFileGroupTitle),
    );
    if (stagedTextLabel && stagedTextModelKey) {
      fromFiles.push({
        id: 'staged-text',
        ownerUserId: userId,
        name: stagedTextLabel,
        extension: 'txt',
        sizeBytes: stagedTextLabel.length,
        modelKey: stagedTextModelKey,
        status: 'pending',
        timeLabel: 'Text entry · not uploaded',
        sourceType: 'text',
        isDemo: false,
        isStagedSelection: true,
      });
    }
    if (stagedJsonLabel && stagedJsonModelKey) {
      fromFiles.push({
        id: 'staged-json',
        ownerUserId: userId,
        name: stagedJsonLabel,
        extension: 'json',
        sizeBytes: stagedJsonLabel.length,
        modelKey: stagedJsonModelKey,
        status: 'pending',
        timeLabel: 'JSON entry · not uploaded',
        sourceType: 'json',
        isDemo: false,
        isStagedSelection: true,
      });
    }
    return fromFiles;
  }, [
    userId,
    stagedFiles,
    stagedFileGroupTitle,
    stagedTextLabel,
    stagedTextModelKey,
    stagedJsonLabel,
    stagedJsonModelKey,
  ]);

  const filtered = useMemo(() => {
    const combined = [...stagedDocuments, ...documents];
    if (statusFilter === 'all') {
      return combined;
    }
    if (statusFilter === 'selected') {
      return combined.filter((doc) => doc.isStagedSelection);
    }
    return combined.filter((doc) => doc.status === statusFilter && !doc.isStagedSelection);
  }, [documents, stagedDocuments, statusFilter]);

  const filterButtons: { id: DocumentStatusFilter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'selected', label: 'Selected' },
    { id: 'uploaded', label: 'Uploaded' },
    { id: 'processing', label: 'Processing' },
    { id: 'processed', label: 'Processed' },
    { id: 'failed', label: 'Failed' },
    { id: 'archived', label: 'Archived' },
  ];

  return (
    <section
      className="flex min-h-0 flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
      data-testid="my-documents-panel"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900">Documents &amp; training status</h2>
          <p className="mt-1 text-xs text-zinc-600">{USER_DATA_ISOLATION_NOTICE}</p>
        </div>
      </div>

      {documentsLoading ? (
        <p className="mt-4 text-sm text-zinc-600" data-testid="documents-loading">
          Loading documents…
        </p>
      ) : null}

      {documentsError ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          <p data-testid="documents-load-error">{documentsError}</p>
          <button
            type="button"
            data-testid="documents-retry-button"
            onClick={onRetryLoad}
            className="mt-2 cursor-pointer text-sm font-medium text-red-900 underline"
          >
            Retry
          </button>
        </div>
      ) : null}

      {trainingJobsError ? (
        <div
          className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
          role="alert"
        >
          <p data-testid="training-jobs-load-error">{trainingJobsError}</p>
          {onRetryTrainingJobs ? (
            <button
              type="button"
              data-testid="training-jobs-retry-button"
              onClick={onRetryTrainingJobs}
              className="mt-2 cursor-pointer text-sm font-medium text-amber-950 underline"
            >
              Retry job status
            </button>
          ) : null}
        </div>
      ) : null}

      <div
        className="mt-4 flex flex-wrap gap-2"
        role="tablist"
        aria-label="Filter documents by status"
        data-testid="document-status-filters"
      >
        {filterButtons.map((filter) => (
          <button
            key={filter.id}
            type="button"
            role="tab"
            aria-selected={statusFilter === filter.id}
            data-testid={`document-filter-${filter.id}`}
            onClick={() => setStatusFilter(filter.id)}
            className={`cursor-pointer rounded-full px-3 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 ${
              statusFilter === filter.id
                ? 'bg-indigo-600 text-white'
                : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {!documentsLoading && !documentsError && documents.length === 0 && stagedDocuments.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-600" data-testid="documents-empty-user">
          No documents for this model yet. Upload files or save text/JSON from the training panel.
        </p>
      ) : null}

      <ul className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto" data-testid="document-list">
        {filtered.map((document) => (
          <TrainingDocumentRow key={document.id} document={document} />
        ))}
        {filtered.length === 0 && !documentsLoading ? (
          <li className="text-sm text-zinc-500" data-testid="document-list-empty">
            No documents match this filter.
          </li>
        ) : null}
      </ul>

      {hasMoreDocuments ? (
        <button
          type="button"
          data-testid="documents-load-more"
          disabled={loadingMore}
          onClick={onLoadMore}
          className="mt-3 cursor-pointer rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loadingMore ? 'Loading…' : 'Load more'}
        </button>
      ) : null}

      <RecentTrainingActivity records={recentActivity} />
    </section>
  );
}
