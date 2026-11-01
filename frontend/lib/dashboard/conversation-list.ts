import type { ConversationSummary } from '@/services/conversation-service';

export function sortConversationsByUpdatedAt(
  conversations: ConversationSummary[],
): ConversationSummary[] {
  return [...conversations].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

export function partitionConversationsByPin(conversations: ConversationSummary[]): {
  pinned: ConversationSummary[];
  recent: ConversationSummary[];
} {
  const sorted = sortConversationsByUpdatedAt(conversations);
  return {
    pinned: sorted.filter((conversation) => conversation.is_pinned),
    recent: sorted.filter((conversation) => !conversation.is_pinned),
  };
}
