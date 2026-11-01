'use client';

import { FormEvent, forwardRef, KeyboardEvent } from 'react';

import { PaperclipIcon, SendIcon } from '@/components/dashboard/icons';

type ChatComposerProps = {
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: (message: string) => void | Promise<void>;
  disabled?: boolean;
  sendDisabled?: boolean;
  placeholder?: string;
};

export const ChatComposer = forwardRef<HTMLTextAreaElement, ChatComposerProps>(function ChatComposer(
  {
  draft,
  onDraftChange,
  onSend,
  disabled = false,
  sendDisabled = false,
  placeholder = 'Ask anything about customs, declarations or HS codes...',
  },
  ref,
) {
  const trimmed = draft.trim();
  const canSend = trimmed.length > 0 && !disabled && !sendDisabled;

  async function submitMessage() {
    if (!trimmed.length || disabled) {
      return;
    }
    await onSend(trimmed);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void submitMessage();
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl" data-testid="chat-composer">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-end gap-1.5 rounded-2xl border border-zinc-200 bg-white px-2.5 py-2 shadow-sm ring-0 transition focus-within:border-indigo-300 focus-within:shadow-md focus-within:ring-2 focus-within:ring-indigo-100 sm:gap-2 sm:px-3">
          <button
            type="button"
            aria-label="Attach file (coming soon)"
            disabled
            data-testid="composer-attach"
            className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <PaperclipIcon className="h-5 w-5" />
          </button>
          <textarea
            ref={ref}
            data-testid="composer-input"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={disabled}
            placeholder={placeholder}
            aria-keyshortcuts="Enter to send, Shift+Enter for new line"
            className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-sm leading-relaxed text-zinc-900 placeholder:text-zinc-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="submit"
            data-testid="composer-send"
            disabled={!canSend}
            aria-label="Send message"
            className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-zinc-200 disabled:text-zinc-400"
          >
            <SendIcon className="h-5 w-5" />
          </button>
        </div>
      </form>
      <p className="mt-2 text-center text-xs text-zinc-500">
        AI responses may require verification. Press Enter to send, Shift+Enter for a new line.
      </p>
    </div>
  );
});
