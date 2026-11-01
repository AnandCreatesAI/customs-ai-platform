import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import { apiFetch } from '@/services/api-client';

export type TrainingJobStatus =
  | 'queued'
  | 'processing'
  | 'retrying'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TrainingJobSummary = {
  id: string;
  business_model: BusinessModelKey;
  document_id: string;
  status: TrainingJobStatus;
  progress: number;
  current_stage: string;
  error_message: string;
  retry_count: number;
  dispatch_error: string;
  created_at: string;
  updated_at: string;
};

export type TrainingJobDocumentSummary = {
  id: string;
  original_filename: string;
  title: string;
  business_model: string;
  input_type: string;
  file_type: string;
  file_size: number;
  status: string;
  created_at: string;
};

export type TrainingJobDetail = TrainingJobSummary & {
  document: TrainingJobDocumentSummary;
  parent_job_id: string | null;
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
};

export type TrainingJobsPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: TrainingJobSummary[];
};

type ApiFailure = {
  ok: false;
  status: number;
  message: string;
  unauthenticated: boolean;
};

function extractDetail(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  if (typeof data === 'object' && data !== null) {
    const record = data as Record<string, unknown>;
    const parts: string[] = [];
    for (const value of Object.values(record)) {
      if (typeof value === 'string') {
        parts.push(value);
      } else if (Array.isArray(value)) {
        for (const item of value) {
          if (typeof item === 'string') {
            parts.push(item);
          }
        }
      }
    }
    if (parts.length > 0) {
      return parts.join(' ');
    }
  }
  return fallback;
}

function failureFromResponse(status: number, data: unknown, fallback: string): ApiFailure {
  if (status === 401) {
    return {
      ok: false,
      status: 401,
      message: extractDetail(data, 'Authentication credentials were not provided.'),
      unauthenticated: true,
    };
  }
  return {
    ok: false,
    status,
    message: extractDetail(data, fallback),
    unauthenticated: false,
  };
}

function isTrainingJobSummary(value: unknown): value is TrainingJobSummary {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.id === 'string' && typeof record.status === 'string';
}

export function parseTrainingJobsPage(data: unknown): TrainingJobsPage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (!Array.isArray(record.results)) {
    return null;
  }
  const results = record.results.filter(isTrainingJobSummary);
  return {
    count: typeof record.count === 'number' ? record.count : results.length,
    next: typeof record.next === 'string' || record.next === null ? record.next : null,
    previous:
      typeof record.previous === 'string' || record.previous === null ? record.previous : null,
    results,
  };
}

export type FetchTrainingJobsResult = { ok: true; page: TrainingJobsPage } | ApiFailure;

export async function fetchTrainingJobs(options?: {
  page?: number;
  pageSize?: number;
  businessModel?: BusinessModelKey | null;
  status?: TrainingJobStatus;
  documentId?: string;
}): Promise<FetchTrainingJobsResult> {
  const params = new URLSearchParams();
  params.set('page', String(options?.page ?? 1));
  params.set('page_size', String(options?.pageSize ?? 50));
  if (options?.businessModel) {
    params.set('business_model', options.businessModel);
  }
  if (options?.status) {
    params.set('status', options.status);
  }
  if (options?.documentId) {
    params.set('document_id', options.documentId);
  }

  try {
    const response = await apiFetch(`/api/training/jobs?${params.toString()}`, {
      method: 'GET',
      cache: 'no-store',
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok) {
      const page = parseTrainingJobsPage(data);
      if (page) {
        return { ok: true, page };
      }
      return failureFromResponse(response.status, data, 'Unexpected training jobs response.');
    }
    return failureFromResponse(response.status, data, 'Unable to load training jobs.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export type CreateTrainingJobsResult =
  | { ok: true; businessModel: string; jobs: TrainingJobSummary[] }
  | ApiFailure;

export async function createTrainingJobs(params: {
  businessModel: BusinessModelKey;
  documentIds: string[];
}): Promise<CreateTrainingJobsResult> {
  try {
    const response = await apiFetch('/api/training/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        business_model: params.businessModel,
        document_ids: params.documentIds,
      }),
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && typeof data === 'object' && data !== null) {
      const record = data as Record<string, unknown>;
      if (Array.isArray(record.jobs)) {
        const jobs = record.jobs.filter(isTrainingJobSummary);
        const businessModel =
          typeof record.business_model === 'string' ? record.business_model : params.businessModel;
        return { ok: true, businessModel, jobs };
      }
    }
    return failureFromResponse(response.status, data, 'Unable to start training jobs.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export const ACTIVE_TRAINING_JOB_STATUSES: TrainingJobStatus[] = [
  'queued',
  'processing',
  'retrying',
];

export function isActiveTrainingJobStatus(status: TrainingJobStatus): boolean {
  return ACTIVE_TRAINING_JOB_STATUSES.includes(status);
}
