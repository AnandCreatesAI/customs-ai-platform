import { apiFetch, CHATBOT_API_TIMEOUT_MS } from '@/services/api-client';

export type PublicChatSuccessResponse = {
  success: true;
  model_key: string;
  provider: string;
  model: string;
  response: string;
  conversation_id: string;
  assistant_message_id: string;
  suggested_questions?: string[];
  sources?: [];
  evidence_status?: string;
};

export type SubmitPublicChatMessageResult =
  | { ok: true; data: PublicChatSuccessResponse }
  | { ok: false; status: number; message: string; code?: string };

function extractErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return fallback;
}

function extractCode(data: unknown): string | undefined {
  if (typeof data === 'object' && data !== null && 'code' in data) {
    const code = (data as { code?: unknown }).code;
    return typeof code === 'string' ? code : undefined;
  }
  return undefined;
}

export async function submitPublicChatMessage(params: {
  message: string;
  clientConversationId?: string | null;
}): Promise<SubmitPublicChatMessageResult> {
  try {
    const body: Record<string, string> = { message: params.message };
    if (params.clientConversationId) {
      body.client_conversation_id = params.clientConversationId;
    }

    const response = await apiFetch('/api/public/chat/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      timeoutMs: CHATBOT_API_TIMEOUT_MS,
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (
      response.ok &&
      typeof data === 'object' &&
      data !== null &&
      (data as { success?: unknown }).success === true
    ) {
      return { ok: true, data: data as PublicChatSuccessResponse };
    }

    return {
      ok: false,
      status: response.status,
      message: extractErrorMessage(data, 'Unable to send your message. Please try again.'),
      code: extractCode(data),
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
    };
  }
}
