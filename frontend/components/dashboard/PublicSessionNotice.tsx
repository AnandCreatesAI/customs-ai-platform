'use client';

import {
  clearPublicChatSessionStorage,
  dismissPublicSessionNotice,
} from '@/lib/public-chat/login-transition';

type PublicSessionNoticeProps = {
  chatCount: number;
  onContinue: () => void;
};

export function PublicSessionNotice({ chatCount, onContinue }: PublicSessionNoticeProps) {
  return (
    <div
      role="dialog"
      aria-labelledby="public-session-notice-title"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 px-4"
    >
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl">
        <h2
          id="public-session-notice-title"
          className="text-lg font-semibold text-zinc-900"
        >
          Public session chats
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600">
          You have {chatCount} temporary chat{chatCount === 1 ? '' : 's'} from the public page in
          this browser. They are not added to your account automatically and are kept separate from
          your saved conversation history.
        </p>
        <p className="mt-2 text-sm leading-relaxed text-zinc-600">
          Continue to your full dashboard with all business models, Employee Space, and private
          history. You can clear the public session when you no longer need those temporary chats.
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
            onClick={() => {
              clearPublicChatSessionStorage();
              onContinue();
            }}
          >
            Clear public session
          </button>
          <button
            type="button"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            onClick={() => {
              dismissPublicSessionNotice();
              onContinue();
            }}
          >
            Continue to dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
