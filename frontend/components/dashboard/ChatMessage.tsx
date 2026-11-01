'use client';

import { useCallback, useState } from 'react';

import { AssistantMarkdown } from '@/components/dashboard/AssistantMarkdown';
import { AssistantMessageActions } from '@/components/dashboard/AssistantMessageActions';
import { EvidenceStatusBadge } from '@/components/dashboard/EvidenceStatusBadge';
import { FollowUpSuggestions } from '@/components/dashboard/FollowUpSuggestions';
import { MessageSourcesPanel } from '@/components/dashboard/MessageSourcesPanel';
import { UserMessageActions } from '@/components/dashboard/UserMessageActions';
import type {
  EvidenceStatus,
  RagEvidenceDetail,
  RagSourceReference,
} from '@/types/rag-types';

export type ChatMessageRole = 'user' | 'assistant';

export type ChatMessageData = {
  id: string;
  role: ChatMessageRole;
  content: string;
  suggestedQuestions?: string[];
  feedbackRating?: number | null;
  sources?: RagSourceReference[];
  evidenceStatus?: EvidenceStatus;
  evidenceDetail?: RagEvidenceDetail;
};

type ChatMessageProps = {
  message: ChatMessageData;
  isRegenerating?: boolean;
  actionsDisabled?: boolean;
  onRegenerate?: (messageId: string) => void;
  onFeedback?: (messageId: string, rating: 1 | -1) => void;
  onFollowUpSelect?: (question: string) => void;
};

export function ChatMessage({
  message,
  isRegenerating = false,
  actionsDisabled = false,
  onRegenerate,
  onFeedback,
  onFollowUpSelect,
}: ChatMessageProps) {
  const [activeSourceRef, setActiveSourceRef] = useState<number | null>(null);

  const handleCitationClick = useCallback((ref: number) => {
    setActiveSourceRef((current) => (current === ref ? null : ref));
  }, []);

  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div
        data-testid="chat-message-user"
        className="group flex w-full flex-col items-end"
      >
        <div className="max-w-[min(85%,42rem)] whitespace-pre-wrap rounded-3xl bg-zinc-900 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {message.content}
        </div>
        <div className="max-w-[min(85%,42rem)]">
          <UserMessageActions content={message.content} />
        </div>
      </div>
    );
  }

  const sources = message.sources ?? [];
  const showEvidence = Boolean(message.evidenceStatus);

  return (
    <div
      data-testid="chat-message-assistant"
      className="group flex w-full justify-start"
    >
      <div className="w-full max-w-[min(100%,46rem)]">
        {isRegenerating ? (
          <p className="mb-2 text-xs text-zinc-500" role="status">
            Regenerating response…
          </p>
        ) : null}
        {showEvidence && message.evidenceStatus ? (
          <EvidenceStatusBadge
            status={message.evidenceStatus}
            detail={message.evidenceDetail}
          />
        ) : null}
        <AssistantMarkdown
          content={message.content}
          sources={sources}
          activeSourceRef={activeSourceRef}
          onCitationClick={handleCitationClick}
        />
        {sources.length > 0 ? (
          <MessageSourcesPanel
            sources={sources}
            activeRef={activeSourceRef}
            onSelectSource={handleCitationClick}
          />
        ) : null}
        {message.suggestedQuestions && onFollowUpSelect ? (
          <FollowUpSuggestions
            questions={message.suggestedQuestions}
            onSelect={onFollowUpSelect}
            disabled={actionsDisabled}
          />
        ) : null}
        <AssistantMessageActions
          content={message.content}
          feedbackRating={message.feedbackRating}
          isRegenerating={isRegenerating}
          onRegenerate={onRegenerate ? () => onRegenerate(message.id) : undefined}
          onFeedback={
            onFeedback ? (rating) => onFeedback(message.id, rating) : undefined
          }
        />
      </div>
    </div>
  );
}
