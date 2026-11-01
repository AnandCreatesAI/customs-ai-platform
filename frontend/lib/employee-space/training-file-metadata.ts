import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import { getFileExtension, validateTrainingFile } from '@/lib/employee-space/training-files';
import type { TrainingFileMetadata } from '@/lib/employee-space/types';

export function buildTrainingFileId(file: File): string {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

export function createTrainingFileMetadata(
  file: File,
  modelKey: BusinessModelKey,
): TrainingFileMetadata {
  return {
    id: buildTrainingFileId(file),
    file,
    name: file.name,
    extension: getFileExtension(file.name),
    sizeBytes: file.size,
    modelKey,
  };
}

export function mergeTrainingFiles(
  current: TrainingFileMetadata[],
  incoming: FileList | File[],
  modelKey: BusinessModelKey,
): { files: TrainingFileMetadata[]; errors: string[] } {
  const list = Array.from(incoming);
  const errors: string[] = [];
  const merged = [...current];

  for (const file of list) {
    const validation = validateTrainingFile(file);
    if (!validation.ok) {
      errors.push(validation.message);
      continue;
    }
    const metadata = createTrainingFileMetadata(file, modelKey);
    if (merged.some((entry) => entry.id === metadata.id)) {
      continue;
    }
    merged.push(metadata);
  }

  return { files: merged, errors };
}
