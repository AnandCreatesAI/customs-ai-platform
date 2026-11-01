'use client';

import { TrainingStatusBadge } from '@/components/employee-space/TrainingStatusBadge';
import { getBusinessModelLabel } from '@/lib/dashboard/business-models';
import type { RecentDocumentActivity } from '@/lib/employee-space/types';

type RecentTrainingActivityProps = {
  records: RecentDocumentActivity[];
};

export function RecentTrainingActivity({ records }: RecentTrainingActivityProps) {
  if (records.length === 0) {
    return null;
  }

  return (
    <section className="mt-6 border-t border-zinc-200 pt-4" data-testid="recent-training-activity">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Recent uploads
      </h3>
      <ul className="mt-3 space-y-2">
        {records.map((record) => (
          <li
            key={record.id}
            data-testid="recent-training-row"
            className="flex flex-col gap-1 rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-zinc-900">{record.sourceName}</p>
              <p className="text-zinc-500">{getBusinessModelLabel(record.modelKey)}</p>
            </div>
            <TrainingStatusBadge status={record.status} />
          </li>
        ))}
      </ul>
    </section>
  );
}
