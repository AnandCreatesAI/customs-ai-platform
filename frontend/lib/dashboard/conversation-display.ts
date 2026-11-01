const PLACEHOLDER_TITLES = new Set(['', 'New conversation', 'Untitled conversation']);

export function formatConversationTitle(title: string): string {
  const trimmed = title.trim();
  if (!trimmed || PLACEHOLDER_TITLES.has(trimmed)) {
    return 'Conversation';
  }
  return trimmed;
}
