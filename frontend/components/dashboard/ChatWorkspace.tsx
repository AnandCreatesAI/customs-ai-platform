'use client';

import { useRef } from 'react';

import { ChatComposer } from '@/components/dashboard/ChatComposer';
import { ChatMessageList } from '@/components/dashboard/ChatMessageList';
import { DashboardWelcome } from '@/components/dashboard/DashboardWelcome';
import type { ChatMessageData } from '@/components/dashboard/ChatMessage';

type ChatWorkspaceProps = {
  messages: ChatMessageData[];
  composerDraft: string;
  onComposerDraftChange: (value: string) => void;
  onSendMessage: (message: string) => void | Promise<void>;
  isSending: boolean;
  isHistoryLoading: boolean;
  historyError: string | null;
  chatError: string | null;
  modelSelectionError?: string | null;
  onClearChatError: () => void;
  composerDisabled?: boolean;
  composerPlaceholder?: string;
  onRetryHistory?: () => void;
  stickToBottomKey?: number;
  regeneratingAssistantId?: string | null;
  onRegenerateAssistant?: (messageId: string) => void;
  onAssistantFeedback?: (messageId: string, rating: 1 | -1) => void;
  onFollowUpSelect?: (question: string) => void;
};

export function ChatWorkspace({
  messages,
  composerDraft,
  onComposerDraftChange,
  onSendMessage,
  isSending,
  isHistoryLoading,
  historyError,
  chatError,
  modelSelectionError = null,
  onClearChatError,
  composerDisabled = false,
  composerPlaceholder,
  onRetryHistory,
  stickToBottomKey = 0,
  regeneratingAssistantId = null,
  onRegenerateAssistant,
  onAssistantFeedback,
  onFollowUpSelect,
}: ChatWorkspaceProps) {
  const composerInputRef = useRef<HTMLTextAreaElement>(null);
  const composerLocked = isSending || isHistoryLoading || Boolean(regeneratingAssistantId);

  return (
    <main data-testid="chat-workspace" className="flex min-h-0 flex-1 flex-col bg-zinc-50/80">
      <ChatMessageList
        messages={messages}
        isAssistantTyping={isSending}
        historyLoading={isHistoryLoading}
        historyError={historyError}
        onRetryHistory={onRetryHistory}
        stickToBottomKey={stickToBottomKey}
        regeneratingAssistantId={regeneratingAssistantId}
        chatActionsDisabled={composerDisabled}
        onRegenerateAssistant={onRegenerateAssistant}
        onAssistantFeedback={onAssistantFeedback}
        onFollowUpSelect={onFollowUpSelect}
        welcome={
          messages.length === 0 && !isHistoryLoading ? <DashboardWelcome /> : null
        }
      />
      <div className="shrink-0 border-t border-zinc-200/90 bg-white/80 px-4 pb-5 pt-3 shadow-[0_-4px_24px_-12px_rgba(0,0,0,0.08)] backdrop-blur-sm">
        {modelSelectionError ? (
          <p
            role="alert"
            data-testid="model-selection-error"
            className="mx-auto mb-3 max-w-3xl text-center text-sm text-amber-800"
          >
            {modelSelectionError}
          </p>
        ) : null}
        {chatError ? (
          <div
            role="alert"
            data-testid="chat-error"
            className="mx-auto mb-3 flex max-w-3xl items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800"
          >
            <p>{chatError}</p>
            <button
              type="button"
              onClick={onClearChatError}
              className="shrink-0 text-xs font-medium underline underline-offset-2"
            >
              Dismiss
            </button>
          </div>
        ) : null}
        <ChatComposer
          ref={composerInputRef}
          draft={composerDraft}
          onDraftChange={onComposerDraftChange}
          onSend={onSendMessage}
          disabled={composerLocked}
          sendDisabled={composerDisabled}
          placeholder={composerPlaceholder}
        />
      </div>
    </main>
  );
}
