'use client';

import { useState } from 'react';

type ConversationRenameDialogProps = {
  open: boolean;
  initialTitle: string;
  onCancel: () => void;
  onSave: (title: string) => void;
};

export function ConversationRenameDialog({
  open,
  initialTitle,
  onCancel,
  onSave,
}: ConversationRenameDialogProps) {
  if (!open) {
    return null;
  }

  return (
    <RenameDialogForm
      key={initialTitle}
      initialTitle={initialTitle}
      onCancel={onCancel}
      onSave={onSave}
    />
  );
}

type RenameDialogFormProps = {
  initialTitle: string;
  onCancel: () => void;
  onSave: (title: string) => void;
};

function RenameDialogForm({ initialTitle, onCancel, onSave }: RenameDialogFormProps) {
  const [title, setTitle] = useState(initialTitle);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="presentation"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-conversation-title"
        data-testid="conversation-rename-dialog"
        className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-4 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="rename-conversation-title" className="text-sm font-semibold text-zinc-900">
          Rename conversation
        </h2>
        <input
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          data-testid="conversation-rename-input"
          className="mt-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-900 focus:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-zinc-200"
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="conversation-rename-save"
            onClick={() => {
              const trimmed = title.trim();
              if (trimmed) {
                onSave(trimmed);
              }
            }}
            className="rounded-xl border border-indigo-600 bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:border-indigo-700 hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
