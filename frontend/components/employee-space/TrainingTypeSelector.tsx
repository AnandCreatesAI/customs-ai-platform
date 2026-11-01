'use client';

import type { TrainingSourceType } from '@/lib/employee-space/types';

type TrainingTypeSelectorProps = {
  value: TrainingSourceType;
  onChange: (value: TrainingSourceType) => void;
};

const OPTIONS: { value: TrainingSourceType; label: string; description: string }[] = [
  {
    value: 'file',
    label: 'File Upload',
    description: 'Upload PDF, Office, spreadsheets, or JSON files.',
  },
  { value: 'text', label: 'Text Input', description: 'Paste training content directly.' },
  { value: 'json', label: 'JSON Input', description: 'Paste structured JSON training payloads.' },
];

export function TrainingTypeSelector({ value, onChange }: TrainingTypeSelectorProps) {
  return (
    <fieldset className="space-y-2" data-testid="training-type-selector">
      <legend className="text-sm font-medium text-zinc-800">Training type</legend>
      <div className="grid gap-3 sm:grid-cols-3">
        {OPTIONS.map((option) => {
          const selected = value === option.value;
          return (
            <label
              key={option.value}
              className={`cursor-pointer rounded-xl border px-4 py-3 transition focus-within:ring-2 focus-within:ring-indigo-200 ${
                selected
                  ? 'border-indigo-300 bg-indigo-50/60 ring-1 ring-indigo-200'
                  : 'border-zinc-200 bg-white hover:border-zinc-300'
              }`}
            >
              <input
                type="radio"
                name="training-type"
                data-testid={`training-type-${option.value}`}
                checked={selected}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              <span className="block text-sm font-semibold text-zinc-900">{option.label}</span>
              <span className="mt-1 block text-xs text-zinc-600">{option.description}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
