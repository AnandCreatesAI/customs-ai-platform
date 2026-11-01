import type { ChatMessageData } from '@/components/dashboard/ChatMessage';
import type { ChatbotRequest, ChatbotSuccessResponse } from '@/services/chatbot-service';
import type { ConversationMessage } from '@/services/conversation-service';
import { parseAssistantRagFromRecord } from '@/types/rag-types';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';
import { isBusinessModelKey } from '@/lib/dashboard/business-models';

export function buildChatbotRequest(
  modelKey: BusinessModelKey,
  message: string,
  activeConversationId: string | null,
): ChatbotRequest {
  const payload: ChatbotRequest = {
    model_key: modelKey,
    message,
  };
  if (activeConversationId) {
    payload.conversation_id = activeConversationId;
  }
  return payload;
}

export function isChatSessionCurrent(
  sessionAtStart: number,
  currentSession: number,
): boolean {
  return sessionAtStart === currentSession;
}

export function shouldAdoptConversationIdFromError(
  requestedConversationId: string | null,
  returnedConversationId: string,
): boolean {
  if (!requestedConversationId) {
    return true;
  }
  return requestedConversationId === returnedConversationId;
}

export function mapHistoryToChatMessages(messages: ConversationMessage[]): ChatMessageData[] {
  return messages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .map((message) => {
      const base = {
        id: message.id,
        role: message.role as 'user' | 'assistant',
        content: message.content,
      };
      if (message.role !== 'assistant') {
        return base;
      }
      return {
        ...base,
        suggestedQuestions: Array.isArray(message.suggested_questions)
          ? message.suggested_questions.filter((item) => typeof item === 'string')
          : undefined,
        feedbackRating:
          typeof message.feedback_rating === 'number' ? message.feedback_rating : null,
        sources: message.sources,
        evidenceStatus: message.evidence_status ?? undefined,
        evidenceDetail: message.evidence_detail ?? undefined,
      };
    });
}

export function mapChatSuccessToAssistantMessage(data: ChatbotSuccessResponse): ChatMessageData {
  const rag = parseAssistantRagFromRecord(
    data as unknown as Record<string, unknown>,
  );
  return {
    id: data.assistant_message_id,
    role: 'assistant',
    content: data.response,
    suggestedQuestions: data.suggested_questions ?? [],
    feedbackRating: null,
    sources: rag.sources.length > 0 ? rag.sources : undefined,
    evidenceStatus: rag.evidenceStatus,
    evidenceDetail: rag.evidenceDetail,
  };
}

export function shouldResetConversationForModelChange(
  activeConversationId: string | null,
  conversationModelKey: BusinessModelKey | null,
  nextModelKey: BusinessModelKey,
): boolean {
  if (!activeConversationId || !conversationModelKey) {
    return false;
  }
  return conversationModelKey !== nextModelKey;
}

export function resolveModelKeyFromConversation(
  modelKey: string,
  fallback: BusinessModelKey,
): BusinessModelKey {
  return isBusinessModelKey(modelKey) ? modelKey : fallback;
}
