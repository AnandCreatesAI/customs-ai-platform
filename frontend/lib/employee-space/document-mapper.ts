import type { DocumentRecord } from '@/services/document-service';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import type { RecentDocumentActivity, UserTrainingDocument } from '@/lib/employee-space/types';

function sourceTypeFromInput(inputType: string): UserTrainingDocument['sourceType'] {
  if (inputType === 'text') {
    return 'text';
  }
  if (inputType === 'json') {
    return 'json';
  }
  return 'file';
}

export function mapDocumentRecordToUserDocument(
  record: DocumentRecord,
  ownerUserId: number,
): UserTrainingDocument {
  const sourceType = sourceTypeFromInput(record.input_type);
  const extension =
    record.file_type ||
    (sourceType === 'json' ? 'json' : sourceType === 'text' ? 'txt' : 'file');

  return {
    id: record.id,
    ownerUserId,
    name: record.title || record.original_filename,
    extension,
    sizeBytes: record.file_size,
    modelKey: record.business_model as BusinessModelKey,
    status: record.status,
    timeLabel: new Date(record.created_at).toLocaleString(),
    sourceType,
    isDemo: false,
  };
}

export function mapDocumentsToRecentActivity(
  documents: UserTrainingDocument[],
): RecentDocumentActivity[] {
  return documents.slice(0, 5).map((doc) => ({
    id: doc.id,
    sourceName: doc.name,
    modelKey: doc.modelKey,
    status: doc.status === 'pending' ? 'uploaded' : doc.status,
    createdAt: doc.timeLabel,
  }));
}
