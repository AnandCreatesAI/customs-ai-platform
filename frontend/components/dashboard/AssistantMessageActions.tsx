'use client';

import { Copy, Loader2, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { copyToClipboard } from '@/services/copy-to-clipboard';

type AssistantMessageActionsProps = {
  content: string;
  feedbackRating?: number | null;
  isRegenerating?: boolean;
  onRegenerate?: () => void;
  onFeedback?: (rating: 1 | -1) => void;
};

export function AssistantMessageActions({
  content,
  feedbackRating = null,
  isRegenerating = false,
  onRegenerate,
  onFeedback,
}: AssistantMessageActionsProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const copiedSuccessfully = await copyToClipboard(content);
    if (!copiedSuccessfully) {
      setCopied(false);
      return;
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div
      className="mt-2 flex min-h-8 items-center gap-0.5 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 md:focus-within:opacity-100"
      data-testid="assistant-message-actions"
    >
      <IconActionButton
        testId="copy-assistant-response"
        label={copied ? 'Copied' : 'Copy'}
        title={copied ? 'Copied' : 'Copy'}
        onClick={() => void handleCopy()}
      >
        <Copy className="h-4 w-4" aria-hidden />
      </IconActionButton>

      {onRegenerate ? (
        <IconActionButton
          testId="regenerate-assistant-response"
          label={isRegenerating ? 'Regenerating response' : 'Regenerate'}
          title="Regenerate"
          disabled={isRegenerating}
          onClick={onRegenerate}
        >
          {isRegenerating ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <RefreshCw className="h-4 w-4" aria-hidden />
          )}
        </IconActionButton>
      ) : null}

      {onFeedback ? (
        <>
          <IconActionButton
            testId="feedback-assistant-up"
            label="Good response"
            title="Good response"
            active={feedbackRating === 1}
            onClick={() => onFeedback(1)}
          >
            <ThumbsUp className="h-4 w-4" aria-hidden />
          </IconActionButton>
          <IconActionButton
            testId="feedback-assistant-down"
            label="Bad response"
            title="Bad response"
            active={feedbackRating === -1}
            onClick={() => onFeedback(-1)}
          >
            <ThumbsDown className="h-4 w-4" aria-hidden />
          </IconActionButton>
        </>
      ) : null}

      {copied ? (
        <span className="ml-1 text-xs font-medium text-emerald-600" role="status">
          Copied
        </span>
      ) : null}
    </div>
  );
}

type IconActionButtonProps = {
  testId: string;
  label: string;
  title: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  children: ReactNode;
};

function IconActionButton({
  testId,
  label,
  title,
  onClick,
  disabled = false,
  active = false,
  children,
}: IconActionButtonProps) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-label={label}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex cursor-pointer items-center justify-center rounded-md p-1.5 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-1 ${
        active
          ? 'bg-zinc-200 text-zinc-900'
          : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800'
      } disabled:cursor-not-allowed disabled:opacity-60`}
    >
      {children}
    </button>
  );
}
