import { apiFetch } from '@/services/api-client';
import type {
  EvidenceStatus,
  RagEvidenceDetail,
  RagSourceReference,
} from '@/types/rag-types';
import { isEvidenceStatus, parseAssistantRagFromRecord } from '@/types/rag-types';

export type ConversationSummary = {
  id: string;
  title: string;
  model_key: string;
  is_pinned?: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ConversationsPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ConversationSummary[];
};

export type ConversationMessage = {
  id: string;
  role: string;
  content: string;
  provider_key: string | null;
  model_name: string | null;
  created_at: string;
  suggested_questions?: string[];
  feedback_rating?: number | null;
  sources?: RagSourceReference[];
  evidence_status?: EvidenceStatus | null;
  evidence_detail?: RagEvidenceDetail | null;
};

export type ConversationMessagesPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ConversationMessage[];
};

export type FetchConversationsResult =
  | { ok: true; page: ConversationsPage }
  | { ok: false; status: number; message: string; unauthenticated: boolean };

export type FetchConversationMessagesResult =
  | { ok: true; messages: ConversationMessage[] }
  | { ok: false; status: number; message: string; unauthenticated: boolean };

export type MutateConversationResult =
  | { ok: true; conversation: ConversationSummary }
  | { ok: false; status: number; message: string; unauthenticated: boolean };

export type DeleteConversationResult =
  | { ok: true }
  | { ok: false; status: number; message: string; unauthenticated: boolean };

function extractDetail(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return fallback;
}

function isConversationSummary(value: unknown): value is ConversationSummary {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === 'string' &&
    typeof record.title === 'string' &&
    typeof record.model_key === 'string'
  );
}

function parseConversationsPage(data: unknown): ConversationsPage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (!Array.isArray(record.results)) {
    return null;
  }
  const results = record.results.filter(isConversationSummary);
  return {
    count: typeof record.count === 'number' ? record.count : results.length,
    next: typeof record.next === 'string' || record.next === null ? record.next : null,
    previous:
      typeof record.previous === 'string' || record.previous === null
        ? record.previous
        : null,
    results,
  };
}

export async function fetchConversations(options?: {
  page?: number;
  pageSize?: number;
}): Promise<FetchConversationsResult> {
  const page = options?.page ?? 1;
  const pageSize = options?.pageSize ?? 20;
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  try {
    const response = await apiFetch(`/api/conversations?${params.toString()}`, {
      method: 'GET',
      cache: 'no-store',
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok) {
      const pageData = parseConversationsPage(data);
      if (pageData) {
        return { ok: true, page: pageData };
      }
      return {
        ok: false,
        status: response.status,
        message: 'Unexpected conversation list format.',
        unauthenticated: false,
      };
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractDetail(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to load conversations. Please try again.'),
      unauthenticated: false,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

function isConversationMessage(value: unknown): value is ConversationMessage {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  if (
    typeof record.id !== 'string' ||
    typeof record.role !== 'string' ||
    typeof record.content !== 'string'
  ) {
    return false;
  }
  return true;
}

function enrichConversationMessage(record: Record<string, unknown>): ConversationMessage {
  const rag = parseAssistantRagFromRecord(record);
  const statusRaw = record.evidence_status;
  const evidenceStatus =
    statusRaw === null
      ? null
      : typeof statusRaw === 'string' && isEvidenceStatus(statusRaw)
        ? statusRaw
        : rag.evidenceStatus ?? undefined;
  return {
    id: String(record.id),
    role: String(record.role),
    content: String(record.content),
    provider_key:
      typeof record.provider_key === 'string' || record.provider_key === null
        ? record.provider_key
        : null,
    model_name:
      typeof record.model_name === 'string' || record.model_name === null
        ? record.model_name
        : null,
    created_at: typeof record.created_at === 'string' ? record.created_at : '',
    suggested_questions: Array.isArray(record.suggested_questions)
      ? record.suggested_questions.filter((item): item is string => typeof item === 'string')
      : undefined,
    feedback_rating:
      typeof record.feedback_rating === 'number' ? record.feedback_rating : null,
    sources: rag.sources.length > 0 ? rag.sources : undefined,
    evidence_status: evidenceStatus ?? null,
    evidence_detail: rag.evidenceDetail ?? null,
  };
}

export async function updateConversationTitle(
  conversationId: string,
  title: string,
): Promise<MutateConversationResult> {
  return updateConversation(conversationId, { title });
}

function parseConversationMessagesPage(data: unknown): ConversationMessagesPage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (!Array.isArray(record.results)) {
    return null;
  }
  return {
    count: typeof record.count === 'number' ? record.count : record.results.length,
    next: typeof record.next === 'string' || record.next === null ? record.next : null,
    previous:
      typeof record.previous === 'string' || record.previous === null
        ? record.previous
        : null,
    results: record.results
      .filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
      .filter(isConversationMessage)
      .map(enrichConversationMessage),
  };
}

async function fetchConversationMessagesPage(
  conversationId: string,
  page: number,
  pageSize: number,
): Promise<
  | { ok: true; page: ConversationMessagesPage }
  | { ok: false; status: number; message: string; unauthenticated: boolean }
> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  try {
    const response = await apiFetch(
      `/api/conversations/${conversationId}/messages?${params.toString()}`,
      {
        method: 'GET',
        cache: 'no-store',
      },
    );

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok) {
      const pageData = parseConversationMessagesPage(data);
      if (pageData) {
        return { ok: true, page: pageData };
      }
      return {
        ok: false,
        status: response.status,
        message: 'Unexpected message history format.',
        unauthenticated: false,
      };
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractDetail(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to load message history. Please try again.'),
      unauthenticated: false,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

const MAX_MESSAGE_HISTORY_PAGES = 20;

export async function updateConversation(
  conversationId: string,
  updates: { title?: string; is_pinned?: boolean },
): Promise<MutateConversationResult> {
  try {
    const response = await apiFetch(`/api/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok && isConversationSummary(data)) {
      return { ok: true, conversation: data };
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractDetail(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to rename conversation. Please try again.'),
      unauthenticated: false,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export async function deleteConversation(
  conversationId: string,
): Promise<DeleteConversationResult> {
  try {
    const response = await apiFetch(`/api/conversations/${conversationId}`, {
      method: 'DELETE',
    });

    if (response.status === 204) {
      return { ok: true };
    }

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractDetail(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to delete conversation. Please try again.'),
      unauthenticated: false,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export async function fetchAllConversationMessages(
  conversationId: string,
  pageSize = 100,
): Promise<FetchConversationMessagesResult> {
  const allMessages: ConversationMessage[] = [];
  let page = 1;

  while (page <= MAX_MESSAGE_HISTORY_PAGES) {
    const result = await fetchConversationMessagesPage(conversationId, page, pageSize);
    if (!result.ok) {
      return result;
    }
    allMessages.push(...result.page.results);
    if (!result.page.next) {
      return { ok: true, messages: allMessages };
    }
    page += 1;
  }

  return { ok: true, messages: allMessages };
}
