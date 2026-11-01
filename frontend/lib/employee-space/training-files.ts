import { formatFileSize } from '@/lib/employee-space/format';

export const TRAINING_ALLOWED_EXTENSIONS = [
  'pdf',
  'docx',
  'doc',
  'txt',
  'xlsx',
  'xls',
  'csv',
  'json',
] as const;

export type TrainingAllowedExtension = (typeof TRAINING_ALLOWED_EXTENSIONS)[number];

export const MAX_TRAINING_FILE_SIZE_BYTES = 26_214_400;
export const MAX_TRAINING_FILE_SIZE_MB = 25;

/** @deprecated Prefer MAX_TRAINING_FILE_SIZE_BYTES */
export const TRAINING_MAX_FILE_SIZE_BYTES = MAX_TRAINING_FILE_SIZE_BYTES;

export function getFileExtension(fileName: string): string {
  const parts = fileName.split('.');
  if (parts.length < 2) {
    return '';
  }
  return parts[parts.length - 1]?.toLowerCase() ?? '';
}

export function isAllowedTrainingExtension(extension: string): extension is TrainingAllowedExtension {
  return (TRAINING_ALLOWED_EXTENSIONS as readonly string[]).includes(extension.toLowerCase());
}

export function validateTrainingFile(file: File): { ok: true } | { ok: false; message: string } {
  const extension = getFileExtension(file.name);
  if (!extension) {
    return { ok: false, message: `${file.name}: file must have a supported extension.` };
  }
  if (!isAllowedTrainingExtension(extension)) {
    return {
      ok: false,
      message: `${file.name}: unsupported type. Allowed: ${TRAINING_ALLOWED_EXTENSIONS.join(', ').toUpperCase()}.`,
    };
  }
  if (file.size > MAX_TRAINING_FILE_SIZE_BYTES) {
    return {
      ok: false,
      message: `${file.name} (${formatFileSize(file.size)}): exceeds the maximum file size of ${MAX_TRAINING_FILE_SIZE_MB} MB.`,
    };
  }
  if (file.size === 0) {
    return { ok: false, message: `${file.name}: file is empty.` };
  }
  return { ok: true };
}
