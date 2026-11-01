import { loadPublicChatStore, persistPublicChatStore } from '@/lib/public-chat/session-store';

export const PUBLIC_LOGIN_TRANSITION_KEY = 'customs-ai.offer-public-import';

/** Call before navigating to /login from the public chat UI. */
export function markLoginFromPublicChat(): void {
  if (typeof window === 'undefined') {
    return;
  }
  sessionStorage.setItem(PUBLIC_LOGIN_TRANSITION_KEY, '1');
}

export function shouldOfferPublicSessionNotice(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  if (sessionStorage.getItem(PUBLIC_LOGIN_TRANSITION_KEY) !== '1') {
    return false;
  }
  return loadPublicChatStore().conversations.length > 0;
}

export function dismissPublicSessionNotice(): void {
  if (typeof window === 'undefined') {
    return;
  }
  sessionStorage.removeItem(PUBLIC_LOGIN_TRANSITION_KEY);
}

export function clearPublicChatSessionStorage(): void {
  persistPublicChatStore({ conversations: [], activeConversationId: null });
  dismissPublicSessionNotice();
}
