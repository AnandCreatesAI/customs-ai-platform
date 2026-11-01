'use client';

import { useMemo, useState } from 'react';

import {
  LogoutIcon,
  PanelLeftCloseIcon,
  PlusIcon,
  SearchIcon,
} from '@/components/dashboard/icons';
import { RecentChatsList } from '@/components/dashboard/RecentChatsList';
import type { AuthUser } from '@/services/auth-service';
import { formatConversationTitle } from '@/lib/dashboard/conversation-display';
import { partitionConversationsByPin } from '@/lib/dashboard/conversation-list';
import type { ConversationSummary } from '@/services/conversation-service';
import {
  platformPrimaryButtonClassName,
  platformPrimarySectionHeadingClassName,
} from '@/lib/platform-primary';

type DashboardSidebarProps = {
  user: AuthUser;
  conversations: ConversationSummary[];
  conversationsLoading: boolean;
  conversationsError: string | null;
  conversationsHasMore: boolean;
  conversationsLoadingMore: boolean;
  onNewChat: () => void;
  onRetryConversations: () => void;
  onLoadMoreConversations: () => void;
  onLogout: () => void;
  isLoggingOut: boolean;
  logoutError: string | null;
  onCollapse?: () => void;
  showCollapseControl?: boolean;
  onNavigate?: () => void;
  className?: string;
  activeConversationId?: string | null;
  onSelectConversation?: (conversation: ConversationSummary) => void;
  onRenameConversation?: (conversation: ConversationSummary, nextTitle: string) => void;
  onDeleteConversation?: (conversation: ConversationSummary) => void;
  onTogglePinConversation?: (conversation: ConversationSummary) => void;
};

function SectionHeading({ children }: { children: string }) {
  return <p className={platformPrimarySectionHeadingClassName}>{children}</p>;
}

export function DashboardSidebar({
  user,
  conversations,
  conversationsLoading,
  conversationsError,
  conversationsHasMore,
  conversationsLoadingMore,
  onNewChat,
  onRetryConversations,
  onLoadMoreConversations,
  onLogout,
  isLoggingOut,
  logoutError,
  onCollapse,
  showCollapseControl = false,
  onNavigate,
  className = '',
  activeConversationId = null,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  onTogglePinConversation,
}: DashboardSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredConversations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) {
      return conversations;
    }
    return conversations.filter((conversation) =>
      formatConversationTitle(conversation.title).toLowerCase().includes(query),
    );
  }, [conversations, searchQuery]);

  const { pinned, recent } = useMemo(
    () => partitionConversationsByPin(filteredConversations),
    [filteredConversations],
  );

  const isFiltering = searchQuery.trim().length > 0;
  const showPinnedSection = pinned.length > 0;
  const listProps = {
    isLoading: conversationsLoading,
    error: conversationsError,
    onRetry: onRetryConversations,
    activeConversationId,
    onSelectConversation: (conversation: ConversationSummary) => {
      onSelectConversation?.(conversation);
      onNavigate?.();
    },
    onRenameConversation,
    onDeleteConversation,
    onTogglePinConversation,
  };

  return (
    <aside
      data-testid="dashboard-sidebar"
      className={`flex h-full w-72 shrink-0 flex-col border-r border-zinc-200/90 bg-white shadow-sm ${className}`}
    >
      <div className="flex items-center gap-3 border-b border-zinc-200/90 px-4 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold tracking-tight text-white shadow-sm">
          CA
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold tracking-tight text-zinc-900">
            Customs AI Platform
          </p>
          <p className="truncate text-xs text-zinc-500">Enterprise workspace</p>
        </div>
        {showCollapseControl ? (
          <button
            type="button"
            data-testid="sidebar-collapse"
            aria-label="Collapse sidebar"
            onClick={onCollapse}
            className="hidden rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800 md:inline-flex"
          >
            <PanelLeftCloseIcon className="h-5 w-5" />
          </button>
        ) : null}
      </div>

      <div className="space-y-3 px-3 pb-3 pt-4">
        <button
          type="button"
          data-testid="new-chat-button"
          onClick={() => {
            onNewChat();
            onNavigate?.();
          }}
          className={`w-full ${platformPrimaryButtonClassName}`}
        >
          <PlusIcon className="h-4 w-4" />
          New Chat
        </button>

        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            type="search"
            data-testid="conversation-search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search conversations"
            aria-label="Search conversations"
            className="w-full rounded-lg border border-zinc-200 bg-zinc-50/80 py-2 pl-9 pr-3 text-sm text-zinc-900 placeholder:text-zinc-400 transition focus:border-indigo-300 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 px-3 pb-3">
        {showPinnedSection ? (
          <div data-testid="sidebar-pinned-section">
            <SectionHeading>Pinned</SectionHeading>
            <RecentChatsList
              {...listProps}
              conversations={pinned}
              hasMore={false}
              isLoadingMore={false}
              onLoadMore={() => {}}
              listTestId="pinned-chats-list"
              emptyMessage="No pinned conversations."
            />
          </div>
        ) : null}

        <div className="flex min-h-0 flex-1 flex-col" data-testid="sidebar-recent-section">
          <SectionHeading>Recent</SectionHeading>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <RecentChatsList
              {...listProps}
              conversations={recent}
              hasMore={conversationsHasMore && !isFiltering}
              isLoadingMore={conversationsLoadingMore}
              onLoadMore={onLoadMoreConversations}
              listTestId="recent-chats-list"
              emptyMessage={
                isFiltering
                  ? 'No matching conversations in your history.'
                  : conversations.length > 0 && recent.length === 0
                    ? 'No recent conversations. Pinned chats appear above.'
                    : undefined
              }
            />
          </div>
        </div>
      </div>

      <div className="border-t border-zinc-200/90 p-3">
        <div className="mb-2 truncate rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2.5 text-xs text-zinc-600">
          <p className="truncate font-medium text-zinc-900">{user.email}</p>
          <p className="capitalize text-zinc-500">{user.role}</p>
        </div>
        {logoutError ? (
          <p className="mb-2 px-2 text-xs text-red-600" role="alert">
            {logoutError}
          </p>
        ) : null}
        <button
          type="button"
          data-testid="logout-button"
          disabled={isLoggingOut}
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100 disabled:opacity-60"
        >
          <LogoutIcon className="h-4 w-4" />
          {isLoggingOut ? 'Signing out…' : 'Log out'}
        </button>
      </div>
    </aside>
  );
}
