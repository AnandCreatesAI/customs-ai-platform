import type { ChatMessageData } from '@/components/dashboard/ChatMessage';
import { DEFAULT_BUSINESS_MODEL_KEY } from '@/lib/dashboard/business-models';
import type { ConversationSummary } from '@/services/conversation-service';

const STORAGE_KEY = 'customs-ai.public-chat.v1';

export type PublicConversationRecord = {
  id: string;
  title: string;
  model_key: string;
  is_pinned: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  messages: ChatMessageData[];
};

type PublicChatStore = {
  conversations: PublicConversationRecord[];
  activeConversationId: string | null;
};

function emptyStore(): PublicChatStore {
  return { conversations: [], activeConversationId: null };
}

function readStore(): PublicChatStore {
  if (typeof window === 'undefined') {
    return emptyStore();
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return emptyStore();
    }
    const parsed = JSON.parse(raw) as PublicChatStore;
    if (!parsed || !Array.isArray(parsed.conversations)) {
      return emptyStore();
    }
    return {
      conversations: parsed.conversations,
      activeConversationId: parsed.activeConversationId ?? null,
    };
  } catch {
    return emptyStore();
  }
}

function writeStore(store: PublicChatStore): void {
  if (typeof window === 'undefined') {
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function loadPublicChatStore(): PublicChatStore {
  return readStore();
}

export function persistPublicChatStore(store: PublicChatStore): void {
  writeStore(store);
}

export function toConversationSummaries(
  records: PublicConversationRecord[],
): ConversationSummary[] {
  return records.map((record) => ({
    id: record.id,
    title: record.title,
    model_key: record.model_key,
    is_pinned: record.is_pinned,
    is_active: record.is_active,
    created_at: record.created_at,
    updated_at: record.updated_at,
  }));
}

export function createPublicConversation(title = 'New chat'): PublicConversationRecord {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title,
    model_key: DEFAULT_BUSINESS_MODEL_KEY,
    is_pinned: false,
    is_active: true,
    created_at: now,
    updated_at: now,
    messages: [],
  };
}

export function deriveConversationTitle(firstUserMessage: string): string {
  const trimmed = firstUserMessage.trim();
  if (!trimmed) {
    return 'New chat';
  }
  return trimmed.length > 48 ? `${trimmed.slice(0, 45)}…` : trimmed;
}
