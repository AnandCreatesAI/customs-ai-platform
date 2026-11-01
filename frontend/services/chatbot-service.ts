import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import {
  parseAssistantRagFromRecord,
  type AssistantRagMetadata,
  type EvidenceStatus,
  type RagEvidenceDetail,
  type RagSourceReference,
} from '@/types/rag-types';

export type ChatbotRequest = {
  model_key: BusinessModelKey;
  message: string;
  conversation_id?: string;
};

export type ChatbotSuccessResponse = {
  success: true;
  model_key: string;
  provider: string;
  model: string;
  response: string;
  conversation_id: string;
  conversation_title?: string;
  assistant_message_id: string;
  suggested_questions?: string[];
  sources?: RagSourceReference[];
  evidence_status?: EvidenceStatus;
  evidence_detail?: RagEvidenceDetail;
};

export type ChatbotRegenerateRequest = {
  model_key: BusinessModelKey;
  conversation_id: string;
  assistant_message_id: string;
};

export type SubmitChatMessageResult =
  | { ok: true; data: ChatbotSuccessResponse }
  | {
      ok: false;
      status: number;
      message: string;
      unauthenticated: boolean;
      conversation_id?: string;
    };

export type RegenerateChatMessageResult = SubmitChatMessageResult;

function extractErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null) {
    if ('detail' in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    }
    const fieldMessages: string[] = [];
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      if (key === 'detail') {
        continue;
      }
      if (Array.isArray(value) && typeof value[0] === 'string') {
        fieldMessages.push(`${key}: ${value[0]}`);
      }
    }
    if (fieldMessages.length > 0) {
      return fieldMessages.join(' ');
    }
  }
  return fallback;
}

function statusFallback(status: number): string {
  if (status === 429) {
    return 'Too many requests. Please wait and try again.';
  }
  if (status === 502) {
    return 'The assistant service returned an invalid response. Please try again.';
  }
  if (status === 503) {
    return 'The assistant service is temporarily unavailable. Please try again.';
  }
  if (status === 504) {
    return 'The assistant request timed out. Please try again.';
  }
  return 'Unable to send your message. Please try again.';
}

function parseSuccessResponse(data: unknown): ChatbotSuccessResponse | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (
    record.success === true &&
    typeof record.response === 'string' &&
    typeof record.conversation_id === 'string' &&
    typeof record.assistant_message_id === 'string'
  ) {
    const suggestions = record.suggested_questions;
    const rag = parseAssistantRagFromRecord(record);
    return {
      ...(data as ChatbotSuccessResponse),
      suggested_questions: Array.isArray(suggestions)
        ? suggestions.filter((item): item is string => typeof item === 'string')
        : [],
      sources: rag.sources.length > 0 ? rag.sources : undefined,
      evidence_status: rag.evidenceStatus,
      evidence_detail: rag.evidenceDetail,
    };
  }
  return null;
}

export function ragFieldsFromChatSuccess(data: ChatbotSuccessResponse): AssistantRagMetadata {
  return {
    sources: data.sources ?? [],
    evidenceStatus: data.evidence_status,
    evidenceDetail: data.evidence_detail,
  };
}

export async function submitChatMessage(
  payload: ChatbotRequest,
): Promise<SubmitChatMessageResult> {
  const body: Record<string, string> = {
    model_key: payload.model_key,
    message: payload.message,
  };
  if (payload.conversation_id) {
    body.conversation_id = payload.conversation_id;
  }

  try {
    const response = await fetch('/api/chatbot/messages', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    const parsed = parseSuccessResponse(data);
    if (response.ok && parsed) {
      return { ok: true, data: parsed };
    }

    const conversationId =
      typeof data === 'object' &&
      data !== null &&
      typeof (data as { conversation_id?: unknown }).conversation_id === 'string'
        ? (data as { conversation_id: string }).conversation_id
        : undefined;

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractErrorMessage(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
        conversation_id: conversationId,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractErrorMessage(data, statusFallback(response.status)),
      unauthenticated: false,
      conversation_id: conversationId,
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

export async function regenerateChatMessage(
  payload: ChatbotRegenerateRequest,
): Promise<RegenerateChatMessageResult> {
  try {
    const response = await fetch('/api/chatbot/regenerate', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    const parsed = parseSuccessResponse(data);
    if (response.ok && parsed) {
      return { ok: true, data: parsed };
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractErrorMessage(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractErrorMessage(data, statusFallback(response.status)),
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

export async function submitMessageFeedback(
  messageId: string,
  rating: 1 | -1,
): Promise<
  | { ok: true; rating: number }
  | { ok: false; status: number; message: string; unauthenticated: boolean }
> {
  try {
    const response = await fetch(`/api/conversations/messages/${messageId}/feedback`, {
      method: 'PUT',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify({ rating }),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok && typeof data === 'object' && data !== null) {
      const record = data as { rating?: unknown };
      if (typeof record.rating === 'number') {
        return { ok: true, rating: record.rating };
      }
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractErrorMessage(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractErrorMessage(data, 'Unable to save feedback.'),
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
