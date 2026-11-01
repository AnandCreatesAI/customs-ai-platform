'use client';

import { ModelSelector } from '@/components/dashboard/ModelSelector';
import type { BusinessModelKey } from '@/lib/dashboard/business-models';

type TrainingModelSelectorProps = {
  selectedKey: BusinessModelKey | null;
  onSelect: (key: BusinessModelKey) => void;
};

export function TrainingModelSelector({ selectedKey, onSelect }: TrainingModelSelectorProps) {
  return (
    <div className="space-y-1.5">
      <p id="training-model-label" className="text-sm font-medium text-zinc-800">
        Select Model <span className="text-red-600">*</span>
      </p>
      <div aria-labelledby="training-model-label" data-testid="training-model-select-wrapper">
        <ModelSelector
          selectedKey={selectedKey}
          onSelect={onSelect}
          triggerTestId="training-model-select"
        />
      </div>
    </div>
  );
}
