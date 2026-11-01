import type { DocumentDisplayStatus, TrainingStatus } from '@/lib/employee-space/types';

type BadgeStatus = DocumentDisplayStatus | TrainingStatus;

const STATUS_STYLES: Record<DocumentDisplayStatus, string> = {
  pending: 'bg-indigo-100 text-indigo-900 ring-indigo-200',
  uploaded: 'bg-amber-100 text-amber-900 ring-amber-200',
  processing: 'bg-amber-100 text-amber-900 ring-amber-200',
  processed: 'bg-emerald-100 text-emerald-900 ring-emerald-200',
  failed: 'bg-red-100 text-red-800 ring-red-200',
  archived: 'bg-zinc-100 text-zinc-700 ring-zinc-200',
};

const STATUS_LABELS: Record<DocumentDisplayStatus, string> = {
  pending: 'Selected',
  uploaded: 'Uploaded',
  processing: 'Processing',
  processed: 'Processed',
  failed: 'Failed',
  archived: 'Archived',
};

function normalizeStatus(status: BadgeStatus): DocumentDisplayStatus {
  if (status === 'running') {
    return 'processing';
  }
  if (status === 'trained') {
    return 'processed';
  }
  if (status === 'pending') {
    return 'pending';
  }
  return status;
}

type TrainingStatusBadgeProps = {
  status: BadgeStatus;
};

export function TrainingStatusBadge({ status }: TrainingStatusBadgeProps) {
  const normalized = normalizeStatus(status);
  return (
    <span
      data-testid="training-status-badge"
      data-status={normalized}
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${STATUS_STYLES[normalized]}`}
    >
      {STATUS_LABELS[normalized]}
    </span>
  );
}
