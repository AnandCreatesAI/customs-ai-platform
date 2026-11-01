'use client';

import { X } from 'lucide-react';

import { TrainingFileIcon } from '@/components/employee-space/TrainingFileIcon';
import { formatFileSize } from '@/lib/employee-space/format';
import type { TrainingFileMetadata } from '@/lib/employee-space/types';

type SelectedFileListProps = {
  files: TrainingFileMetadata[];
  groupTitle?: string | null;
  onRemove: (id: string) => void;
};

export function SelectedFileList({ files, groupTitle, onRemove }: SelectedFileListProps) {
  if (files.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2" data-testid="selected-file-list">
      {groupTitle ? (
        <p className="text-sm font-semibold text-indigo-900" data-testid="selected-file-group-title">
          {groupTitle}
        </p>
      ) : null}
      <p className="text-sm font-medium text-zinc-700" data-testid="selected-file-count">
        {files.length} {files.length === 1 ? 'file' : 'files'} selected
      </p>
      <ul className="space-y-2">
        {files.map((file) => (
          <li
            key={file.id}
            data-testid="selected-file-row"
            data-filename={file.name}
            className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-white px-3 py-2.5"
          >
            <TrainingFileIcon extension={file.extension} />
            <div className="min-w-0 flex-1">
              <p
                className="truncate text-sm font-medium text-zinc-900"
                data-testid="selected-file-name"
              >
                {file.name}
              </p>
              <p className="text-xs text-zinc-500" data-testid="selected-file-meta">
                <span data-testid="selected-file-extension">{file.extension.toUpperCase()}</span>
                {' · '}
                <span data-testid="selected-file-size">{formatFileSize(file.sizeBytes)}</span>
              </p>
            </div>
            <button
              type="button"
              data-testid={`remove-file-${file.id}`}
              aria-label={`Remove ${file.name}`}
              onClick={() => onRemove(file.id)}
              className="cursor-pointer rounded-md p-1.5 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
            >
              <X className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
