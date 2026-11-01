'use client';

import { type ReactNode, useState } from 'react';
import { createPortal } from 'react-dom';

type TrainingModalShellProps = {
  open: boolean;
  title: string;
  modelLabel: string | null;
  onClose: () => void;
  onBack?: () => void;
  backLabel?: string;
  children: ReactNode;
  footer?: ReactNode;
  testId?: string;
};

export function TrainingModalShell({
  open,
  title,
  modelLabel,
  onClose,
  onBack,
  backLabel = 'Back',
  children,
  footer,
  testId = 'training-modal',
}: TrainingModalShellProps) {
  const [portalTarget] = useState<HTMLElement | null>(() =>
    typeof document === 'undefined' ? null : document.body,
  );

  if (!open || !portalTarget) {
    return null;
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/40 p-4 sm:items-center"
      role="presentation"
      onClick={onClose}
      data-testid={`${testId}-overlay`}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${testId}-title`}
        data-testid={testId}
        className="flex max-h-[min(90dvh,720px)] w-full max-w-lg flex-col rounded-xl border border-zinc-200 bg-white shadow-xl"
        onClick={(event) => event.stopPropagation()}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-zinc-100 px-4 py-3">
          <div className="min-w-0">
            <h2 id={`${testId}-title`} className="text-sm font-semibold text-zinc-900">
              {title}
            </h2>
            {modelLabel ? (
              <p
                className="mt-1 text-xs font-medium text-indigo-800"
                data-testid="training-modal-business-model"
              >
                Business model: {modelLabel}
              </p>
            ) : (
              <p className="mt-1 text-xs text-amber-800" data-testid="training-modal-model-missing">
                Select a business model in the left panel before submitting.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid={`${testId}-close`}
            className="shrink-0 rounded-lg px-2 py-1 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
          >
            Close
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{children}</div>

        {footer ? (
          <div className="shrink-0 border-t border-zinc-100 px-4 py-3">{footer}</div>
        ) : null}

        {onBack ? (
          <div className="shrink-0 border-t border-zinc-100 px-4 py-2">
            <button
              type="button"
              onClick={onBack}
              data-testid={`${testId}-back`}
              className="text-sm font-medium text-indigo-700 underline-offset-2 hover:underline"
            >
              {backLabel}
            </button>
          </div>
        ) : null}
      </div>
    </div>,
    portalTarget,
  );
}
