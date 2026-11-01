'use client';

import { FileSpreadsheet, FileText } from 'lucide-react';

import { TrainingProgressBar } from '@/components/employee-space/TrainingProgressBar';
import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { formatFileSize } from '@/lib/employee-space/format';
import type { DemoQueueItem } from '@/lib/employee-space/types';

type TrainingFileRowProps = {
  item: DemoQueueItem;
};

function FileIcon({ extension }: { extension: string }) {
  const spreadsheet = ['xlsx', 'xls', 'csv'].includes(extension.toLowerCase());
  const Icon = spreadsheet ? FileSpreadsheet : FileText;
  return <Icon className="h-8 w-8 shrink-0 text-zinc-500" aria-hidden />;
}

export function TrainingFileRow({ item }: TrainingFileRowProps) {
  const displayName = `${item.fileName}.${item.extension}`;

  return (
    <li
      data-testid="training-file-row"
      data-demo={item.isDemo ? 'true' : 'false'}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3">
          <FileIcon extension={item.extension} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-zinc-900">{displayName}</p>
            <p className="text-xs text-zinc-500">
              {formatFileSize(item.sizeBytes)} · {item.timeLabel}
            </p>
            {item.isDemo ? (
              <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-zinc-400">
                Demonstration data
              </p>
            ) : null}
          </div>
        </div>
        <TrainingStatusBadge status={item.status} />
      </div>
      <div className="mt-4">
        <TrainingProgressBar percent={item.progressPercent} status={item.status} />
      </div>
      {item.status === 'failed' && item.failureReason ? (
        <p className="mt-3 text-sm text-red-600" role="alert">
          {item.failureReason}
        </p>
      ) : null}
      {item.status === 'trained' ? (
        <p className="mt-3 text-xs text-zinc-500">Demo UI — no model weights were updated.</p>
      ) : null}
    </li>
  );
}
