'use client';

import { TrainingFileRow } from '@/components/employee-space/TrainingFileRow';
import type { DemoQueueItem } from '@/lib/employee-space/types';

type TrainingQueueProps = {
  items: DemoQueueItem[];
};

export function TrainingQueue({ items }: TrainingQueueProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-zinc-500" data-testid="training-queue-empty">
        No items in the training queue yet.
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="training-queue">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-zinc-900">Training queue</h3>
        <span className="text-xs text-zinc-500">Demo progress states</span>
      </div>
      <ul className="space-y-3">
        {items.map((item) => (
          <TrainingFileRow key={item.id} item={item} />
        ))}
      </ul>
    </div>
  );
}
