'use client';

import { Check } from 'lucide-react';

import { BUSINESS_MODELS, type BusinessModelKey } from '@/lib/dashboard/business-models';

type ModelSelectionPanelProps = {
  selectedKey: BusinessModelKey | null;
  onSelect: (key: BusinessModelKey) => void;
};

export function ModelSelectionPanel({ selectedKey, onSelect }: ModelSelectionPanelProps) {
  return (
    <aside
      className="flex min-h-0 flex-col rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
      data-testid="model-selection-panel"
      aria-label="Model selection"
    >
      <h2 className="text-sm font-semibold text-zinc-900">Select Model</h2>
      <p className="mt-1 text-xs text-zinc-600">
        Choose which business model will receive file and text training from this workspace.
      </p>
      <ul className="mt-4 space-y-2" role="listbox" aria-label="Business models">
        {BUSINESS_MODELS.map((model) => {
          const selected = selectedKey === model.key;
          return (
            <li key={model.key}>
              <button
                type="button"
                role="option"
                aria-selected={selected}
                data-testid={`model-option-card-${model.key}`}
                onClick={() => onSelect(model.key)}
                className={`w-full cursor-pointer rounded-lg border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 ${
                  selected
                    ? 'border-indigo-400 bg-indigo-50 ring-1 ring-indigo-200'
                    : 'border-zinc-200 bg-white hover:border-indigo-200 hover:bg-zinc-50'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold text-zinc-900">{model.label}</span>
                  {selected ? (
                    <Check className="h-4 w-4 shrink-0 text-indigo-700" aria-hidden />
                  ) : null}
                </div>
                <p className="mt-1 text-xs leading-snug text-zinc-600">{model.description}</p>
              </button>
            </li>
          );
        })}
      </ul>
      {selectedKey ? (
        <p className="mt-4 text-xs font-medium text-indigo-800" data-testid="model-selection-active">
          Active: {BUSINESS_MODELS.find((m) => m.key === selectedKey)?.label}
        </p>
      ) : (
        <p className="mt-4 text-xs text-amber-800" data-testid="model-selection-required">
          Select a model before training.
        </p>
      )}
    </aside>
  );
}
