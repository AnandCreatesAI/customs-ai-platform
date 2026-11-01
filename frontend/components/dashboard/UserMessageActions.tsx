'use client';

import { Copy } from 'lucide-react';
import { useState } from 'react';

import { copyToClipboard } from '@/services/copy-to-clipboard';

type UserMessageActionsProps = {
  content: string;
};

export function UserMessageActions({ content }: UserMessageActionsProps) {
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
      className="mt-1.5 flex min-h-8 items-center justify-end gap-0.5 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100 md:focus-within:opacity-100"
      data-testid="user-message-actions"
    >
      <button
        type="button"
        data-testid="copy-user-message"
        aria-label={copied ? 'Copied' : 'Copy'}
        title={copied ? 'Copied' : 'Copy'}
        onClick={() => void handleCopy()}
        className="inline-flex cursor-pointer items-center justify-center rounded-md p-1.5 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-1"
      >
        <Copy className="h-4 w-4" aria-hidden />
      </button>
      {copied ? (
        <span className="text-xs font-medium text-emerald-600" role="status">
          Copied
        </span>
      ) : null}
    </div>
  );
}
