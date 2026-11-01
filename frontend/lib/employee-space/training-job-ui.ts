import type { TrainingJobStatus } from '@/services/training-job-service';

export type TrainingBadgeTone =
  | 'yellow'
  | 'blue'
  | 'orange'
  | 'green'
  | 'red'
  | 'grey';

const STAGE_LABELS: Record<string, string> = {
  queued: 'Queued',
  processing: 'Processing',
  resolve_document: 'Document extraction',
  prepare_workspace: 'Document extraction',
  convert_legacy: 'Document extraction',
  extract: 'Document extraction',
  ocr: 'Document extraction',
  vision_optional: 'Document extraction',
  normalize: 'Text normalization',
  validate_quality: 'Text normalization',
  persist_artifact: 'Document extraction',
  extraction_complete: 'Document extraction',
  chunk: 'Chunking',
  chunk_persisted: 'Chunking',
  embed: 'Embedding',
  embed_complete: 'Embedding',
  finalize: 'Finalizing pipeline',
  completed: 'Completed',
  cancelled: 'Cancelled',
  extraction_failed: 'Extraction failed',
  chunking_failed: 'Chunking failed',
  embedding_failed: 'Embedding failed',
  processing_error: 'Processing error',
  validation_failed: 'Validation failed',
  worker_interrupted: 'Worker interrupted',
  soft_time_limit: 'Time limit exceeded',
};

export function formatTrainingStage(stage: string): string {
  const key = stage.trim().toLowerCase();
  if (!key) {
    return '—';
  }
  return STAGE_LABELS[key] ?? stage.replace(/_/g, ' ');
}

export function trainingJobBadge(status: TrainingJobStatus): {
  label: string;
  tone: TrainingBadgeTone;
} {
  switch (status) {
    case 'queued':
      return { label: 'Queued', tone: 'yellow' };
    case 'processing':
      return { label: 'Processing', tone: 'blue' };
    case 'retrying':
      return { label: 'Retrying', tone: 'orange' };
    case 'completed':
      return { label: 'Trained', tone: 'green' };
    case 'failed':
      return { label: 'Failed', tone: 'red' };
    case 'cancelled':
      return { label: 'Cancelled', tone: 'grey' };
    default:
      return { label: status, tone: 'grey' };
  }
}

export function documentStatusBadge(status: string): { label: string; tone: TrainingBadgeTone } {
  switch (status) {
    case 'uploaded':
      return { label: 'Uploaded', tone: 'yellow' };
    case 'processing':
      return { label: 'Processing', tone: 'blue' };
    case 'processed':
      return { label: 'Trained', tone: 'green' };
    case 'failed':
      return { label: 'Failed', tone: 'red' };
    case 'archived':
      return { label: 'Archived', tone: 'grey' };
    case 'pending':
      return { label: 'Selected', tone: 'yellow' };
    default:
      return { label: status, tone: 'grey' };
  }
}

export function toneToBadgeClassName(tone: TrainingBadgeTone): string {
  switch (tone) {
    case 'yellow':
      return 'bg-amber-100 text-amber-900 ring-amber-200';
    case 'blue':
      return 'bg-sky-100 text-sky-900 ring-sky-200';
    case 'orange':
      return 'bg-orange-100 text-orange-900 ring-orange-200';
    case 'green':
      return 'bg-emerald-100 text-emerald-900 ring-emerald-200';
    case 'red':
      return 'bg-red-100 text-red-800 ring-red-200';
    case 'grey':
      return 'bg-zinc-100 text-zinc-700 ring-zinc-200';
    default:
      return 'bg-zinc-100 text-zinc-700 ring-zinc-200';
  }
}

export function progressBarColorForJob(status: TrainingJobStatus): string {
  if (status === 'completed') {
    return 'bg-emerald-500';
  }
  if (status === 'failed') {
    return 'bg-red-500';
  }
  if (status === 'retrying') {
    return 'bg-orange-500';
  }
  if (status === 'cancelled') {
    return 'bg-zinc-400';
  }
  if (status === 'queued') {
    return 'bg-amber-500';
  }
  return 'bg-sky-500';
}
