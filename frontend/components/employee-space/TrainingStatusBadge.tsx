import {
  documentStatusBadge,
  toneToBadgeClassName,
  trainingJobBadge,
  type TrainingBadgeTone,
} from '@/lib/employee-space/training-job-ui';
import type { DocumentDisplayStatus, TrainingStatus } from '@/lib/employee-space/types';
import type { TrainingJobStatus } from '@/services/training-job-service';

type BadgeStatus = DocumentDisplayStatus | TrainingStatus;

type TrainingStatusBadgeProps = {
  status: BadgeStatus;
  trainingJobStatus?: TrainingJobStatus | null;
};

function normalizeDocumentStatus(status: BadgeStatus): DocumentDisplayStatus {
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

export function TrainingStatusBadge({ status, trainingJobStatus }: TrainingStatusBadgeProps) {
  let label: string;
  let tone: TrainingBadgeTone;

  if (trainingJobStatus) {
    const jobBadge = trainingJobBadge(trainingJobStatus);
    label = jobBadge.label;
    tone = jobBadge.tone;
  } else {
    const docBadge = documentStatusBadge(normalizeDocumentStatus(status));
    label = docBadge.label;
    tone = docBadge.tone;
  }

  return (
    <span
      data-testid="training-status-badge"
      data-status={trainingJobStatus ?? normalizeDocumentStatus(status)}
      className={`inline-flex shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${toneToBadgeClassName(tone)}`}
    >
      {label}
    </span>
  );
}
