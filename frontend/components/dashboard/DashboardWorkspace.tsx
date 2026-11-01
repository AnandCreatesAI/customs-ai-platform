'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { ChatWorkspace } from '@/components/dashboard/ChatWorkspace';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import type { ChatMessageData } from '@/components/dashboard/ChatMessage';
import type { AuthUser } from '@/services/auth-service';
import {
  regenerateChatMessage,
  submitChatMessage,
  submitMessageFeedback,
  type ChatbotSuccessResponse,
} from '@/services/chatbot-service';
import {
  deleteConversation,
  fetchAllConversationMessages,
  fetchConversations,
  updateConversation,
  updateConversationTitle,
  type ConversationSummary,
} from '@/services/conversation-service';
import {
  buildChatbotRequest,
  isChatSessionCurrent,
  mapChatSuccessToAssistantMessage,
  mapHistoryToChatMessages,
  resolveModelKeyFromConversation,
  shouldAdoptConversationIdFromError,
  shouldResetConversationForModelChange,
} from '@/lib/dashboard/chat-session-mapping';
import {
  COMPOSER_MODEL_REQUIRED_PLACEHOLDER,
  DEFAULT_BUSINESS_MODEL_KEY,
  MODEL_SELECTION_VALIDATION_MESSAGE,
  type BusinessModelKey,
} from '@/lib/dashboard/business-models';
import { sortConversationsByUpdatedAt } from '@/lib/dashboard/conversation-list';

const CONVERSATIONS_PAGE_SIZE = 20;

type DashboardWorkspaceProps = {
  user: AuthUser;
  onLogout: () => Promise<void>;
  isLoggingOut: boolean;
  logoutError: string | null;
  onSessionExpired: () => void;
};

export function DashboardWorkspace({
  user,
  onLogout,
  isLoggingOut,
  logoutError,
  onSessionExpired,
}: DashboardWorkspaceProps) {
  const [selectedModelKey, setSelectedModelKey] = useState<BusinessModelKey | null>(null);
  const [modelSelectionError, setModelSelectionError] = useState<string | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [desktopSidebarCollapsed, setDesktopSidebarCollapsed] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [conversationsLoadingMore, setConversationsLoadingMore] = useState(false);
  const [conversationsError, setConversationsError] = useState<string | null>(null);
  const [nextPage, setNextPage] = useState<number | null>(null);

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversationModelKey, setConversationModelKey] = useState<BusinessModelKey | null>(
    null,
  );
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [composerDraft, setComposerDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [regeneratingAssistantId, setRegeneratingAssistantId] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [stickToBottomKey, setStickToBottomKey] = useState(0);
  const [historyRetryConversation, setHistoryRetryConversation] =
    useState<ConversationSummary | null>(null);

  const activeConversationIdRef = useRef<string | null>(null);
  const chatSessionGenerationRef = useRef(0);

  const bumpChatSession = useCallback(() => {
    chatSessionGenerationRef.current += 1;
  }, []);

  const applyActiveConversationId = useCallback((conversationId: string | null) => {
    activeConversationIdRef.current = conversationId;
    setActiveConversationId(conversationId);
  }, []);

  const applyConversationsResult = useCallback(
    (result: Awaited<ReturnType<typeof fetchConversations>>, page: number, append: boolean) => {
      if (result.ok) {
        setConversations((current) =>
          append ? [...current, ...result.page.results] : result.page.results,
        );
        setNextPage(result.page.next ? page + 1 : null);
        setConversationsError(null);
        return;
      }

      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }

      setConversationsError(result.message);
    },
    [onSessionExpired],
  );

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const result = await fetchConversations({
        page: 1,
        pageSize: CONVERSATIONS_PAGE_SIZE,
      });
      if (cancelled) {
        return;
      }
      applyConversationsResult(result, 1, false);
      setConversationsLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [applyConversationsResult]);

  const reloadConversations = useCallback(async () => {
    setConversationsLoading(true);
    setConversationsError(null);
    const result = await fetchConversations({ page: 1, pageSize: CONVERSATIONS_PAGE_SIZE });
    applyConversationsResult(result, 1, false);
    setConversationsLoading(false);
  }, [applyConversationsResult]);

  const loadMoreConversations = useCallback(async () => {
    if (nextPage === null) {
      return;
    }
    setConversationsLoadingMore(true);
    const result = await fetchConversations({
      page: nextPage,
      pageSize: CONVERSATIONS_PAGE_SIZE,
    });
    applyConversationsResult(result, nextPage, true);
    setConversationsLoadingMore(false);
  }, [applyConversationsResult, nextPage]);

  const loadConversationHistory = useCallback(
    async (conversation: ConversationSummary) => {
      bumpChatSession();
      const sessionAtLoad = chatSessionGenerationRef.current;
      const requestedConversationId = conversation.id;

      setIsHistoryLoading(true);
      setHistoryError(null);
      setChatError(null);
      applyActiveConversationId(requestedConversationId);
      setHistoryRetryConversation(conversation);

      const modelKey = resolveModelKeyFromConversation(
        conversation.model_key,
        DEFAULT_BUSINESS_MODEL_KEY,
      );
      setSelectedModelKey(modelKey);
      setConversationModelKey(modelKey);
      setModelSelectionError(null);
      setMessages([]);

      const result = await fetchAllConversationMessages(requestedConversationId);
      setIsHistoryLoading(false);

      if (
        !isChatSessionCurrent(sessionAtLoad, chatSessionGenerationRef.current) ||
        activeConversationIdRef.current !== requestedConversationId
      ) {
        return;
      }

      if (result.ok) {
        setMessages(mapHistoryToChatMessages(result.messages));
        setStickToBottomKey((value) => value + 1);
        return;
      }

      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }

      setHistoryError(result.message);
      setMessages([]);
    },
    [applyActiveConversationId, bumpChatSession, onSessionExpired],
  );

  const mergeAssistantFromResponse = useCallback(
    (data: ChatbotSuccessResponse): ChatMessageData => mapChatSuccessToAssistantMessage(data),
    [],
  );

  const handleRenameConversation = useCallback(
    async (conversation: ConversationSummary, nextTitle: string) => {
      const result = await updateConversationTitle(conversation.id, nextTitle);
      if (result.ok) {
        setConversations((current) =>
          current.map((entry) =>
            entry.id === conversation.id ? { ...entry, title: result.conversation.title } : entry,
          ),
        );
        return;
      }
      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }
      setConversationsError(result.message);
    },
    [onSessionExpired],
  );

  const handleTogglePinConversation = useCallback(
    async (conversation: ConversationSummary) => {
      const previousPinned = Boolean(conversation.is_pinned);
      const optimisticPinned = !previousPinned;

      setConversations((current) =>
        sortConversationsByUpdatedAt(
          current.map((entry) =>
            entry.id === conversation.id ? { ...entry, is_pinned: optimisticPinned } : entry,
          ),
        ),
      );

      const result = await updateConversation(conversation.id, {
        is_pinned: optimisticPinned,
      });
      if (result.ok) {
        setConversations((current) =>
          sortConversationsByUpdatedAt(
            current.map((entry) =>
              entry.id === conversation.id
                ? { ...entry, is_pinned: result.conversation.is_pinned }
                : entry,
            ),
          ),
        );
        return;
      }

      setConversations((current) =>
        sortConversationsByUpdatedAt(
          current.map((entry) =>
            entry.id === conversation.id ? { ...entry, is_pinned: previousPinned } : entry,
          ),
        ),
      );

      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }
      setConversationsError(result.message);
    },
    [onSessionExpired],
  );

  const resetToNewChat = useCallback(() => {
    bumpChatSession();
    applyActiveConversationId(null);
    setConversationModelKey(null);
    setMessages([]);
    setComposerDraft('');
    setIsSending(false);
    setChatError(null);
    setHistoryError(null);
    setHistoryRetryConversation(null);
    setSelectedModelKey(null);
    setModelSelectionError(null);
    setStickToBottomKey((value) => value + 1);
  }, [applyActiveConversationId, bumpChatSession]);

  const handleDeleteConversation = useCallback(
    async (conversation: ConversationSummary) => {
      const result = await deleteConversation(conversation.id);
      if (result.ok) {
        setConversations((current) => current.filter((entry) => entry.id !== conversation.id));
        if (activeConversationIdRef.current === conversation.id) {
          resetToNewChat();
        }
        return;
      }
      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }
      setConversationsError(result.message);
    },
    [onSessionExpired, resetToNewChat],
  );

  function handleModelSelect(nextModelKey: BusinessModelKey) {
    if (
      shouldResetConversationForModelChange(
        activeConversationIdRef.current,
        conversationModelKey,
        nextModelKey,
      )
    ) {
      bumpChatSession();
      applyActiveConversationId(null);
      setConversationModelKey(null);
      setMessages([]);
      setHistoryError(null);
      setHistoryRetryConversation(null);
    }
    setSelectedModelKey(nextModelKey);
    setModelSelectionError(null);
  }

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (isSending || isHistoryLoading) {
        return;
      }

      if (!selectedModelKey) {
        setModelSelectionError(MODEL_SELECTION_VALIDATION_MESSAGE);
        return;
      }

      const sessionAtSend = chatSessionGenerationRef.current;
      const requestedConversationId = activeConversationIdRef.current;

      setIsSending(true);
      setChatError(null);
      setStickToBottomKey((value) => value + 1);

      const tempUserId = `pending-user-${Date.now()}`;
      setMessages((current) => [
        ...current,
        { id: tempUserId, role: 'user', content: message },
      ]);

      const result = await submitChatMessage(
        buildChatbotRequest(selectedModelKey, message, requestedConversationId),
      );

      const sessionStillCurrent = isChatSessionCurrent(
        sessionAtSend,
        chatSessionGenerationRef.current,
      );

      if (!sessionStillCurrent) {
        setIsSending(false);
        return;
      }

      if (result.ok) {
        setMessages((current) => {
          const withoutPending = current.filter((entry) => entry.id !== tempUserId);
          return [
            ...withoutPending,
            { id: tempUserId, role: 'user', content: message },
            mergeAssistantFromResponse(result.data),
          ];
        });
        applyActiveConversationId(result.data.conversation_id);
        setConversationModelKey(
          resolveModelKeyFromConversation(result.data.model_key, selectedModelKey),
        );
        setComposerDraft('');
        void reloadConversations();
        setIsSending(false);
        return;
      }

      if (result.unauthenticated) {
        setMessages((current) => current.filter((entry) => entry.id !== tempUserId));
        setComposerDraft(message);
        onSessionExpired();
        setIsSending(false);
        return;
      }

      if (
        result.conversation_id &&
        shouldAdoptConversationIdFromError(requestedConversationId, result.conversation_id)
      ) {
        applyActiveConversationId(result.conversation_id);
        const history = await fetchAllConversationMessages(result.conversation_id);
        if (
          isChatSessionCurrent(sessionAtSend, chatSessionGenerationRef.current) &&
          activeConversationIdRef.current === result.conversation_id
        ) {
          if (history.ok) {
            setMessages(mapHistoryToChatMessages(history.messages));
          } else {
            setMessages((current) => current.filter((entry) => entry.id !== tempUserId));
          }
        }
      } else {
        setMessages((current) => current.filter((entry) => entry.id !== tempUserId));
      }

      setComposerDraft(message);
      setChatError(result.message);
      setIsSending(false);
    },
    [
      applyActiveConversationId,
      isHistoryLoading,
      isSending,
      onSessionExpired,
      reloadConversations,
      mergeAssistantFromResponse,
      selectedModelKey,
    ],
  );

  const handleFollowUpSelect = useCallback(
    (question: string) => {
      void handleSendMessage(question);
    },
    [handleSendMessage],
  );

  const handleRegenerateAssistant = useCallback(
    async (assistantMessageId: string) => {
      const conversationId = activeConversationIdRef.current;
      if (!conversationId || !selectedModelKey || regeneratingAssistantId || isSending) {
        return;
      }

      const sessionAtRegenerate = chatSessionGenerationRef.current;
      setRegeneratingAssistantId(assistantMessageId);
      setChatError(null);

      const result = await regenerateChatMessage({
        model_key: selectedModelKey,
        conversation_id: conversationId,
        assistant_message_id: assistantMessageId,
      });

      if (
        !isChatSessionCurrent(sessionAtRegenerate, chatSessionGenerationRef.current) ||
        activeConversationIdRef.current !== conversationId
      ) {
        setRegeneratingAssistantId(null);
        return;
      }

      if (result.ok) {
        setMessages((current) =>
          current.map((entry) =>
            entry.id === assistantMessageId
              ? mergeAssistantFromResponse(result.data)
              : entry,
          ),
        );
        setRegeneratingAssistantId(null);
        return;
      }

      if (result.unauthenticated) {
        onSessionExpired();
        setRegeneratingAssistantId(null);
        return;
      }

      setChatError(result.message);
      setRegeneratingAssistantId(null);
    },
    [
      isSending,
      mergeAssistantFromResponse,
      onSessionExpired,
      regeneratingAssistantId,
      selectedModelKey,
    ],
  );

  const handleAssistantFeedback = useCallback(
    async (messageId: string, rating: 1 | -1) => {
      const result = await submitMessageFeedback(messageId, rating);
      if (result.ok) {
        setMessages((current) =>
          current.map((entry) =>
            entry.id === messageId ? { ...entry, feedbackRating: result.rating } : entry,
          ),
        );
        return;
      }
      if (result.unauthenticated) {
        onSessionExpired();
        return;
      }
      setChatError(result.message);
    },
    [onSessionExpired],
  );

  const sidebarProps = {
    user,
    conversations,
    conversationsLoading,
    conversationsError,
    conversationsHasMore: nextPage !== null,
    conversationsLoadingMore,
    onNewChat: resetToNewChat,
    onRetryConversations: () => void reloadConversations(),
    onLoadMoreConversations: () => void loadMoreConversations(),
    onLogout: () => void onLogout(),
    isLoggingOut,
    logoutError,
    activeConversationId,
    onSelectConversation: (conversation: ConversationSummary) => {
      void loadConversationHistory(conversation);
    },
    onRenameConversation: (conversation: ConversationSummary, nextTitle: string) => {
      void handleRenameConversation(conversation, nextTitle);
    },
    onDeleteConversation: (conversation: ConversationSummary) => {
      void handleDeleteConversation(conversation);
    },
    onTogglePinConversation: (conversation: ConversationSummary) => {
      void handleTogglePinConversation(conversation);
    },
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
          selectedModelKey={selectedModelKey}
          onModelSelect={handleModelSelect}
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
          isHistoryLoading={isHistoryLoading}
          historyError={historyError}
          chatError={chatError}
          modelSelectionError={modelSelectionError}
          composerDisabled={selectedModelKey === null}
          composerPlaceholder={
            selectedModelKey === null ? COMPOSER_MODEL_REQUIRED_PLACEHOLDER : undefined
          }
          onClearChatError={() => setChatError(null)}
          onRetryHistory={
            historyRetryConversation
              ? () => void loadConversationHistory(historyRetryConversation)
              : undefined
          }
          stickToBottomKey={stickToBottomKey}
          regeneratingAssistantId={regeneratingAssistantId}
          onRegenerateAssistant={(messageId) => void handleRegenerateAssistant(messageId)}
          onAssistantFeedback={(messageId, rating) =>
            void handleAssistantFeedback(messageId, rating)
          }
          onFollowUpSelect={handleFollowUpSelect}
        />
      </div>
    </div>
  );
}
