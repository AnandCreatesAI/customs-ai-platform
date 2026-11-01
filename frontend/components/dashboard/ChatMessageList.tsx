'use client';

import { type ReactNode, useRef } from 'react';

import { ChatMessage, type ChatMessageData } from '@/components/dashboard/ChatMessage';
import { useChatAutoScroll } from '@/hooks/use-chat-auto-scroll';

type ChatMessageListProps = {
  messages?: ChatMessageData[];
  welcome: ReactNode | null;
  isAssistantTyping?: boolean;
  historyLoading?: boolean;
  historyError?: string | null;
  onRetryHistory?: () => void;
  stickToBottomKey?: number;
  regeneratingAssistantId?: string | null;
  chatActionsDisabled?: boolean;
  onRegenerateAssistant?: (messageId: string) => void;
  onAssistantFeedback?: (messageId: string, rating: 1 | -1) => void;
  onFollowUpSelect?: (question: string) => void;
};

export function ChatMessageList({
  messages = [],
  welcome,
  isAssistantTyping = false,
  historyLoading = false,
  historyError = null,
  onRetryHistory,
  stickToBottomKey = 0,
  regeneratingAssistantId = null,
  chatActionsDisabled = false,
  onRegenerateAssistant,
  onAssistantFeedback,
  onFollowUpSelect,
}: ChatMessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const hasMessages = messages.length > 0;

  useChatAutoScroll(
    scrollContainerRef,
    messages.length + (isAssistantTyping ? 1 : 0) + (historyLoading ? 1 : 0) + stickToBottomKey,
  );

  return (
    <div
      ref={scrollContainerRef}
      data-testid="message-history"
      className="min-h-0 flex-1 overflow-y-auto overscroll-contain pb-2"
    >
      <div
        className={`mx-auto flex w-full flex-col gap-5 px-4 py-6 md:gap-6 md:py-8 ${
          hasMessages || historyLoading ? 'max-w-3xl' : 'max-w-4xl min-h-full justify-center'
        }`}
      >
        {historyLoading ? (
          <p className="text-center text-sm text-zinc-500" role="status">
            Loading conversation…
          </p>
        ) : null}

        {historyError ? (
          <div
            role="alert"
            className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          >
            <p>{historyError}</p>
            {onRetryHistory ? (
              <button
                type="button"
                onClick={onRetryHistory}
                className="mt-2 text-xs font-medium underline underline-offset-2"
              >
                Retry loading
              </button>
            ) : null}
          </div>
        ) : null}

        {!hasMessages && !historyLoading && !historyError && welcome ? welcome : null}

        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            message={message}
            isRegenerating={regeneratingAssistantId === message.id}
            actionsDisabled={chatActionsDisabled}
            onRegenerate={onRegenerateAssistant}
            onFeedback={onAssistantFeedback}
            onFollowUpSelect={onFollowUpSelect}
          />
        ))}

        {isAssistantTyping ? (
          <div className="flex justify-start" data-testid="assistant-typing" role="status">
            <div className="inline-flex items-center gap-1 rounded-2xl bg-zinc-100 px-4 py-3 text-sm text-zinc-500">
              <span className="sr-only">Assistant is typing</span>
              <span className="typing-dot h-2 w-2 rounded-full bg-zinc-400" />
              <span className="typing-dot animation-delay-150 h-2 w-2 rounded-full bg-zinc-400" />
              <span className="typing-dot animation-delay-300 h-2 w-2 rounded-full bg-zinc-400" />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
