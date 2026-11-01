'use client';

import { useEffect, useId, useRef, useState } from 'react';

import { dashboardHeaderButtonClassName } from '@/lib/dashboard/dashboard-header-button-styles';
import { ChevronDownIcon } from '@/components/dashboard/icons';
import {
  BUSINESS_MODELS,
  MODEL_SELECTOR_PLACEHOLDER,
  type BusinessModelKey,
  getBusinessModelLabel,
} from '@/lib/dashboard/business-models';

type ModelSelectorProps = {
  selectedKey: BusinessModelKey | null;
  onSelect: (key: BusinessModelKey) => void;
  triggerTestId?: string;
  appearance?: 'default' | 'header';
};

export function ModelSelector({
  selectedKey,
  onSelect,
  triggerTestId = 'model-selector-trigger',
  appearance = 'default',
}: ModelSelectorProps) {
  const listboxId = useId();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const selectedLabel = selectedKey ? getBusinessModelLabel(selectedKey) : MODEL_SELECTOR_PLACEHOLDER;
  const headerTriggerLabel = selectedKey ? selectedLabel : MODEL_SELECTOR_PLACEHOLDER;

  const triggerClassName =
    appearance === 'header'
      ? `${dashboardHeaderButtonClassName} min-w-[9.5rem] justify-between border-indigo-600`
      : `flex max-w-[min(100%,16rem)] items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium shadow-sm transition hover:border-indigo-200 hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300 focus-visible:ring-offset-1 ${
          selectedKey ? 'text-zinc-900' : 'text-zinc-600'
        }`;

  return (
    <div ref={containerRef} className="relative min-w-0">
      <button
        type="button"
        data-testid={triggerTestId}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        onClick={() => setOpen((value) => !value)}
        className={triggerClassName}
      >
        <span className="truncate">
          {appearance === 'header' ? headerTriggerLabel : selectedLabel}
        </span>
        <ChevronDownIcon
          className={`h-4 w-4 shrink-0 ${appearance === 'header' ? 'text-white' : 'text-zinc-500'}`}
        />
      </button>

      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Business models"
          data-testid="model-selector-list"
          className="absolute left-0 z-30 mt-2 w-72 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-zinc-200 bg-white py-1 shadow-lg ring-1 ring-black/5"
        >
          {BUSINESS_MODELS.map((model) => {
            const isSelected = selectedKey !== null && model.key === selectedKey;
            return (
              <li key={model.key} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  data-testid={`model-option-${model.key}`}
                  onClick={() => {
                    onSelect(model.key);
                    setOpen(false);
                  }}
                  className={`flex w-full flex-col items-start gap-0.5 px-3 py-2.5 text-left text-sm transition ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-950'
                      : 'text-zinc-700 hover:bg-zinc-50'
                  }`}
                >
                  <span className="font-medium">{model.label}</span>
                  <span className="text-xs text-zinc-500">
                    {model.description}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
