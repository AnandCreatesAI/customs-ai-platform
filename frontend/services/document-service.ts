import type { BusinessModelKey } from '@/lib/dashboard/business-models';

export type DocumentBackendStatus =
  | 'uploaded'
  | 'processing'
  | 'processed'
  | 'failed'
  | 'archived';

export type DocumentRecord = {
  id: string;
  original_filename: string;
  title: string;
  business_model: BusinessModelKey;
  input_type: 'file' | 'text' | 'json' | string;
  file_type: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  status: DocumentBackendStatus;
  created_at: string;
  updated_at: string;
};

export type DocumentsPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: DocumentRecord[];
};

export type UploadFileResultEntry =
  | { status: 'created'; document: DocumentRecord }
  | { status: 'error'; filename: string; error: string };

export type UploadFilesResponse = {
  business_model: string;
  results: UploadFileResultEntry[];
};

export type TextJsonSubmitResponse = {
  id: string;
  title: string;
  business_model: string;
  input_type: string;
  status: DocumentBackendStatus;
  document: DocumentRecord;
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

function isDocumentRecord(value: unknown): value is DocumentRecord {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.id === 'string' && typeof record.status === 'string';
}

export function parseDocumentsPage(data: unknown): DocumentsPage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (!Array.isArray(record.results)) {
    return null;
  }
  const pageRecord = data as DocumentsPage;
  const results = pageRecord.results.filter(isDocumentRecord);
  return {
    count: typeof pageRecord.count === 'number' ? pageRecord.count : results.length,
    next: typeof pageRecord.next === 'string' || pageRecord.next === null ? pageRecord.next : null,
    previous:
      typeof pageRecord.previous === 'string' || pageRecord.previous === null
        ? pageRecord.previous
        : null,
    results,
  };
}

export type FetchDocumentsResult =
  | { ok: true; page: DocumentsPage }
  | ApiFailure;

export async function fetchDocuments(options?: {
  page?: number;
  pageSize?: number;
  businessModel?: BusinessModelKey | null;
  status?: DocumentBackendStatus;
}): Promise<FetchDocumentsResult> {
  const params = new URLSearchParams();
  params.set('page', String(options?.page ?? 1));
  params.set('page_size', String(options?.pageSize ?? 20));
  if (options?.businessModel) {
    params.set('business_model', options.businessModel);
  }
  if (options?.status) {
    params.set('status', options.status);
  }

  try {
    const response = await fetch(`/api/documents?${params.toString()}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
      cache: 'no-store',
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok) {
      const page = parseDocumentsPage(data);
      if (page) {
        return { ok: true, page };
      }
      return failureFromResponse(response.status, data, 'Unexpected document list format.');
    }
    return failureFromResponse(response.status, data, 'Unable to load documents.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export type UploadFilesResult = { ok: true; data: UploadFilesResponse } | ApiFailure;

export async function uploadTrainingFiles(params: {
  businessModel: BusinessModelKey;
  title?: string;
  files: File[];
}): Promise<UploadFilesResult> {
  const formData = new FormData();
  formData.append('business_model', params.businessModel);
  if (params.title?.trim()) {
    formData.append('title', params.title.trim());
  }
  for (const file of params.files) {
    formData.append('files', file);
  }

  try {
    const response = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && typeof data === 'object' && data !== null && Array.isArray((data as UploadFilesResponse).results)) {
      return { ok: true, data: data as UploadFilesResponse };
    }
    return failureFromResponse(response.status, data, 'File upload failed.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export type SubmitTextResult = { ok: true; data: TextJsonSubmitResponse } | ApiFailure;

export async function submitTrainingText(params: {
  businessModel: BusinessModelKey;
  title: string;
  content: string;
}): Promise<SubmitTextResult> {
  try {
    const response = await fetch('/api/documents/text', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        business_model: params.businessModel,
        title: params.title,
        content: params.content,
      }),
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && typeof data === 'object' && data !== null && 'document' in data) {
      return { ok: true, data: data as TextJsonSubmitResponse };
    }
    return failureFromResponse(response.status, data, 'Unable to save text input.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export type SubmitJsonResult = { ok: true; data: TextJsonSubmitResponse } | ApiFailure;

export async function submitTrainingJson(params: {
  businessModel: BusinessModelKey;
  title: string;
  content: string;
}): Promise<SubmitJsonResult> {
  try {
    const response = await fetch('/api/documents/json', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        business_model: params.businessModel,
        title: params.title,
        content: params.content,
      }),
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && typeof data === 'object' && data !== null && 'document' in data) {
      return { ok: true, data: data as TextJsonSubmitResponse };
    }
    return failureFromResponse(response.status, data, 'Unable to save JSON input.');
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}
