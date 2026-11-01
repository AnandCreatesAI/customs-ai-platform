'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ChatWorkspace } from '@/components/dashboard/ChatWorkspace';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import type { ChatMessageData } from '@/components/dashboard/ChatMessage';
import {
  createPublicConversation,
  deriveConversationTitle,
  loadPublicChatStore,
  persistPublicChatStore,
  toConversationSummaries,
  type PublicConversationRecord,
} from '@/lib/public-chat/session-store';
import { sortConversationsByUpdatedAt } from '@/lib/dashboard/conversation-list';

function sortPublicRecords(records: PublicConversationRecord[]): PublicConversationRecord[] {
  return sortConversationsByUpdatedAt(toConversationSummaries(records)).map((summary) => {
    const match = records.find((entry) => entry.id === summary.id);
    if (!match) {
      throw new Error('Missing public conversation record during sort.');
    }
    return match;
  });
}
import { markLoginFromPublicChat } from '@/lib/public-chat/login-transition';
import { platformPrimaryButtonClassName } from '@/lib/platform-primary';
import { submitPublicChatMessage } from '@/services/public-chat-service';
import type { ConversationSummary } from '@/services/conversation-service';

function mapAssistantMessage(
  assistantMessageId: string,
  content: string,
  suggestedQuestions?: string[],
): ChatMessageData {
  return {
    id: assistantMessageId,
    role: 'assistant',
    content,
    suggestedQuestions: suggestedQuestions,
  };
}

function readInitialPublicState(): {
  conversations: PublicConversationRecord[];
  activeConversationId: string | null;
  messages: ChatMessageData[];
} {
  if (typeof window === 'undefined') {
    return { conversations: [], activeConversationId: null, messages: [] };
  }
  const store = loadPublicChatStore();
  const active = store.conversations.find((entry) => entry.id === store.activeConversationId);
  return {
    conversations: store.conversations,
    activeConversationId: store.activeConversationId,
    messages: active?.messages ?? [],
  };
}

export function PublicChatClient() {
  const [initialStore] = useState(readInitialPublicState);
  const [conversations, setConversations] = useState<PublicConversationRecord[]>(
    initialStore.conversations,
  );
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    initialStore.activeConversationId,
  );
  const [messages, setMessages] = useState<ChatMessageData[]>(initialStore.messages);
  const [composerDraft, setComposerDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [desktopSidebarCollapsed, setDesktopSidebarCollapsed] = useState(false);
  const [stickToBottomKey, setStickToBottomKey] = useState(0);

  const conversationSummaries = useMemo(
    () => toConversationSummaries(sortPublicRecords(conversations)),
    [conversations],
  );

  const persist = useCallback(
    (nextConversations: PublicConversationRecord[], nextActiveId: string | null) => {
      persistPublicChatStore({
        conversations: nextConversations,
        activeConversationId: nextActiveId,
      });
    },
    [],
  );

  const skipInitialPersistRef = useRef(true);

  useEffect(() => {
    if (skipInitialPersistRef.current) {
      skipInitialPersistRef.current = false;
      return;
    }
    persist(conversations, activeConversationId);
  }, [conversations, activeConversationId, persist]);

  const selectConversation = useCallback(
    (summary: ConversationSummary) => {
      const record = conversations.find((entry) => entry.id === summary.id);
      if (!record) {
        return;
      }
      setActiveConversationId(record.id);
      setMessages(record.messages);
      setChatError(null);
      setStickToBottomKey((value) => value + 1);
    },
    [conversations],
  );

  const resetToNewChat = useCallback(() => {
    const created = createPublicConversation();
    setConversations((current) => [created, ...current]);
    setActiveConversationId(created.id);
    setMessages([]);
    setComposerDraft('');
    setChatError(null);
    setStickToBottomKey((value) => value + 1);
  }, []);

  const handleRenameConversation = useCallback(
    (conversation: ConversationSummary, nextTitle: string) => {
      setConversations((current) =>
        current.map((entry) =>
          entry.id === conversation.id
            ? { ...entry, title: nextTitle.trim() || entry.title, updated_at: new Date().toISOString() }
            : entry,
        ),
      );
    },
    [],
  );

  const handleDeleteConversation = useCallback(
    (conversation: ConversationSummary) => {
      setConversations((current) => current.filter((entry) => entry.id !== conversation.id));
      if (activeConversationId === conversation.id) {
        setActiveConversationId(null);
        setMessages([]);
        setComposerDraft('');
        setChatError(null);
      }
    },
    [activeConversationId],
  );

  const handleTogglePinConversation = useCallback((conversation: ConversationSummary) => {
    setConversations((current) =>
      sortPublicRecords(
        current.map((entry) =>
          entry.id === conversation.id
            ? { ...entry, is_pinned: !entry.is_pinned, updated_at: new Date().toISOString() }
            : entry,
        ),
      ),
    );
  }, []);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (isSending) {
        return;
      }

      let conversationId = activeConversationId;
      let conversationRecords = conversations;

      if (!conversationId) {
        const created = createPublicConversation(deriveConversationTitle(message));
        conversationRecords = [created, ...conversations];
        conversationId = created.id;
        setConversations(conversationRecords);
        setActiveConversationId(conversationId);
      }

      const sessionConversationId = conversationId;
      setIsSending(true);
      setChatError(null);
      setStickToBottomKey((value) => value + 1);

      const tempUserId = `public-user-${Date.now()}`;
      const pendingMessages: ChatMessageData[] = [
        ...messages,
        { id: tempUserId, role: 'user', content: message },
      ];
      setMessages(pendingMessages);

      const result = await submitPublicChatMessage({
        message,
        clientConversationId: sessionConversationId,
      });

      if (!result.ok) {
        setMessages(messages);
        setComposerDraft(message);
        setChatError(result.message);
        setIsSending(false);
        return;
      }

      const assistant = mapAssistantMessage(
        result.data.assistant_message_id,
        result.data.response,
        result.data.suggested_questions,
      );
      const finalMessages: ChatMessageData[] = [
        ...messages.filter((entry) => entry.id !== tempUserId),
        { id: tempUserId, role: 'user', content: message },
        assistant,
      ];
      setMessages(finalMessages);
      setComposerDraft('');

      const now = new Date().toISOString();
      setConversations((current) =>
        sortPublicRecords(
          current.map((entry) => {
            if (entry.id !== sessionConversationId) {
              return entry;
            }
            const title =
              entry.messages.length === 0 ? deriveConversationTitle(message) : entry.title;
            return {
              ...entry,
              title,
              updated_at: now,
              messages: finalMessages,
            };
          }),
        ),
      );

      setIsSending(false);
    },
    [activeConversationId, conversations, isSending, messages],
  );

  const sidebarProps = {
    variant: 'public' as const,
    conversations: conversationSummaries,
    conversationsLoading: false,
    conversationsError: null,
    conversationsHasMore: false,
    conversationsLoadingMore: false,
    onNewChat: resetToNewChat,
    onRetryConversations: () => {},
    onLoadMoreConversations: () => {},
    onLogout: () => {},
    isLoggingOut: false,
    logoutError: null,
    activeConversationId,
    onSelectConversation: selectConversation,
    onRenameConversation: handleRenameConversation,
    onDeleteConversation: handleDeleteConversation,
    onTogglePinConversation: handleTogglePinConversation,
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-zinc-100">
      {!desktopSidebarCollapsed ? (
        <div className="hidden md:flex">
          <DashboardSidebar
            {...sidebarProps}
            showCollapseControl
            onCollapse={() => setDesktopSidebarCollapsed(true)}
          />
        </div>
      ) : null}

      {mobileSidebarOpen ? (
        <>
          <button
            type="button"
            aria-label="Close sidebar"
            className="fixed inset-0 z-40 bg-black/40 md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 md:hidden">
            <DashboardSidebar
              {...sidebarProps}
              onNavigate={() => setMobileSidebarOpen(false)}
            />
          </div>
        </>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <DashboardHeader
          mode="public"
          trailingActions={
            <Link
              href="/login"
              data-testid="header-login"
              className={platformPrimaryButtonClassName}
              onClick={() => markLoginFromPublicChat()}
            >
              Log in
            </Link>
          }
          onToggleMobileSidebar={() => setMobileSidebarOpen((open) => !open)}
          desktopSidebarCollapsed={desktopSidebarCollapsed}
          onExpandDesktopSidebar={() => setDesktopSidebarCollapsed(false)}
        />
        <ChatWorkspace
          messages={messages}
          composerDraft={composerDraft}
          onComposerDraftChange={setComposerDraft}
          onSendMessage={handleSendMessage}
          isSending={isSending}
          isHistoryLoading={false}
          historyError={null}
          chatError={chatError}
          onClearChatError={() => setChatError(null)}
          stickToBottomKey={stickToBottomKey}
          onFollowUpSelect={(question) => void handleSendMessage(question)}
        />
      </div>
    </div>
  );
}
