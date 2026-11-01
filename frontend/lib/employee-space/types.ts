import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import type { DocumentBackendStatus } from '@/services/document-service';

/** Local-only status for files/text/json not yet submitted to the backend. */
export type StagedDocumentStatus = 'pending';

export type DocumentDisplayStatus = DocumentBackendStatus | StagedDocumentStatus;

/** @deprecated Demo-only training job statuses; prefer DocumentBackendStatus. */
export type TrainingStatus = 'pending' | 'running' | 'trained' | 'failed';

export type TrainingSourceType = 'file' | 'text' | 'json';

export type TrainingFileMetadata = {
  id: string;
  file: File;
  name: string;
  extension: string;
  sizeBytes: number;
  modelKey: BusinessModelKey;
};

export type UserTrainingDocument = {
  id: string;
  ownerUserId: number;
  name: string;
  extension: string;
  sizeBytes: number;
  modelKey: BusinessModelKey;
  status: DocumentDisplayStatus;
  timeLabel: string;
  failureReason?: string;
  sourceType: TrainingSourceType;
  isDemo: boolean;
  isStagedSelection?: boolean;
};

export type RecentDocumentActivity = {
  id: string;
  sourceName: string;
  modelKey: BusinessModelKey;
  status: DocumentBackendStatus;
  createdAt: string;
};

export type DemoQueueItem = {
  id: string;
  fileName: string;
  extension: string;
  sizeBytes: number;
  modelKey: BusinessModelKey;
  status: TrainingStatus;
  progressPercent: number;
  timeLabel: string;
  failureReason?: string;
  isDemo: true;
};

export type DemoManagedFile = {
  id: string;
  name: string;
  extension: string;
  sizeBytes: number;
  modelKey: BusinessModelKey;
  status: TrainingStatus;
  progressPercent?: number;
  failureReason?: string;
  uploadedAt: string;
  isDemo: true;
};

export type DemoTrainingHistoryRecord = {
  id: string;
  jobId: string;
  modelKey: BusinessModelKey;
  sourceName: string;
  sourceType: TrainingSourceType;
  startedAt: string;
  completedAt: string | null;
  progressPercent: number;
  status: TrainingStatus;
  failureReason?: string;
  isDemo: true;
};

export type DocumentStatusFilter = TrainingStatus | 'all' | 'selected';
