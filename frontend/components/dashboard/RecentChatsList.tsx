'use client';

import { useEffect, useRef, useState } from 'react';

import { ConversationRenameDialog } from '@/components/dashboard/ConversationRenameDialog';
import { ChatBubbleIcon, MoreHorizontalIcon } from '@/components/dashboard/icons';
import { formatConversationTitle } from '@/lib/dashboard/conversation-display';
import type { ConversationSummary } from '@/services/conversation-service';

type RecentChatsListProps = {
  conversations: ConversationSummary[];
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  isLoadingMore: boolean;
  onRetry: () => void;
  onLoadMore: () => void;
  emptyMessage?: string;
  listTestId?: string;
  activeConversationId?: string | null;
  onSelectConversation?: (conversation: ConversationSummary) => void;
  onRenameConversation?: (conversation: ConversationSummary, nextTitle: string) => void;
  onDeleteConversation?: (conversation: ConversationSummary) => void;
  onTogglePinConversation?: (conversation: ConversationSummary) => void;
};

type ConversationRowProps = {
  conversation: ConversationSummary;
  isActive: boolean;
  onSelect?: (conversation: ConversationSummary) => void;
  onRename?: (conversation: ConversationSummary, nextTitle: string) => void;
  onDelete?: (conversation: ConversationSummary) => void;
  onTogglePin?: (conversation: ConversationSummary) => void;
};

function ConversationRow({
  conversation,
  isActive,
  onSelect,
  onRename,
  onDelete,
  onTogglePin,
}: ConversationRowProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const displayTitle = formatConversationTitle(conversation.title);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [menuOpen]);

  function handleRenameClick() {
    setMenuOpen(false);
    onRename?.(conversation, displayTitle);
  }

  function handleDelete() {
    setMenuOpen(false);
    const confirmed = window.confirm(`Delete "${displayTitle}"? This cannot be undone.`);
    if (!confirmed) {
      return;
    }
    onDelete?.(conversation);
  }

  const showActions = Boolean(onRename || onDelete || onTogglePin);

  return (
    <li className="relative">
      <div
        className={`group flex w-full items-center gap-1 rounded-lg pr-1 transition ${
          isActive
            ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-200/80'
            : 'hover:bg-zinc-100'
        }`}
      >
        <button
          type="button"
          title={displayTitle}
          data-testid={`conversation-item-${conversation.id}`}
          aria-current={isActive ? 'true' : undefined}
          onClick={() => onSelect?.(conversation)}
          className={`flex min-w-0 flex-1 items-center gap-2 px-2.5 py-2 text-left text-sm ${
            isActive ? 'font-medium text-indigo-950' : 'text-zinc-700'
          }`}
        >
          <ChatBubbleIcon
            className={`h-4 w-4 shrink-0 ${
              isActive ? 'text-indigo-600' : 'text-zinc-400 group-hover:text-zinc-600'
            }`}
          />
              <span className="truncate">{displayTitle}</span>
        </button>
        {showActions ? (
          <div className="relative shrink-0" ref={menuRef}>
            <button
              type="button"
              aria-label={`Actions for ${displayTitle}`}
              aria-expanded={menuOpen}
              data-testid={`conversation-menu-${conversation.id}`}
              onClick={(event) => {
                event.stopPropagation();
                setMenuOpen((open) => !open);
              }}
              className="rounded-md p-1.5 text-zinc-500 opacity-100 transition hover:bg-zinc-200/80 hover:text-zinc-800 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
            >
              <MoreHorizontalIcon className="h-4 w-4" />
            </button>
            {menuOpen ? (
              <div
                role="menu"
                data-testid={`conversation-menu-panel-${conversation.id}`}
                className="absolute right-0 top-full z-20 mt-1 min-w-[9rem] rounded-lg border border-zinc-200 bg-white py-1 shadow-lg"
              >
                {onTogglePin ? (
                  <button
                    type="button"
                    role="menuitem"
                    data-testid={`conversation-pin-${conversation.id}`}
                    onClick={() => {
                      setMenuOpen(false);
                      onTogglePin(conversation);
                    }}
                    className="block w-full px-3 py-2 text-left text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                  >
                    {conversation.is_pinned ? 'Unpin' : 'Pin'}
                  </button>
                ) : null}
                {onRename ? (
                  <button
                    type="button"
                    role="menuitem"
                    data-testid={`conversation-rename-${conversation.id}`}
                    onClick={handleRenameClick}
                    className="block w-full px-3 py-2 text-left text-xs font-medium text-zinc-700 hover:bg-zinc-50"
                  >
                    Rename
                  </button>
                ) : null}
                {onDelete ? (
                  <button
                    type="button"
                    role="menuitem"
                    data-testid={`conversation-delete-${conversation.id}`}
                    onClick={handleDelete}
                    className="block w-full px-3 py-2 text-left text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}

export function RecentChatsList({
  conversations,
  isLoading,
  error,
  hasMore,
  isLoadingMore,
  onRetry,
  onLoadMore,
  emptyMessage,
  listTestId = 'recent-chats-list',
  activeConversationId = null,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
}: RecentChatsListProps) {
  const [renameTarget, setRenameTarget] = useState<{
    conversation: ConversationSummary;
    title: string;
  } | null>(null);
  if (isLoading) {
    return (
      <p className="px-2 py-1 text-xs text-zinc-500" role="status">
        Loading conversations…
      </p>
    );
  }

  if (error) {
    return (
      <div className="space-y-2 px-2">
        <p className="text-xs text-red-600" role="alert">
          {error}
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="text-xs font-medium text-zinc-700 underline-offset-2 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <p className="px-2 py-1 text-xs text-zinc-500">
        {emptyMessage ?? 'No conversations yet. Send a message to start one.'}
      </p>
    );
  }

  return (
    <div className="flex min-h-0 flex-col gap-1">
      <ConversationRenameDialog
        open={renameTarget !== null}
        initialTitle={renameTarget?.title ?? ''}
        onCancel={() => setRenameTarget(null)}
        onSave={(title) => {
          if (renameTarget) {
            onRenameConversation?.(renameTarget.conversation, title);
          }
          setRenameTarget(null);
        }}
      />
      <ul className="space-y-0.5" data-testid={listTestId}>
        {conversations.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            isActive={conversation.id === activeConversationId}
            onSelect={onSelectConversation}
            onRename={(target, currentTitle) =>
              setRenameTarget({ conversation: target, title: currentTitle })
            }
            onDelete={onDeleteConversation}
            onTogglePin={onTogglePinConversation}
          />
        ))}
      </ul>
      {hasMore ? (
        <button
          type="button"
          data-testid="conversations-load-more"
          disabled={isLoadingMore}
          onClick={onLoadMore}
          className="mx-2 mt-1 rounded-md px-2 py-1.5 text-left text-xs font-medium text-zinc-600 transition hover:bg-zinc-100 disabled:opacity-60"
        >
          {isLoadingMore ? 'Loading…' : 'View more'}
        </button>
      ) : null}
    </div>
  );
}
