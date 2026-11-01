'use client';

import {
  JSON_TRAINING_PLACEHOLDER,
  prettyPrintTrainingJson,
  validateTrainingJson,
  type JsonValidationResult,
} from '@/lib/employee-space/json-training';

type JsonTrainingEditorProps = {
  title: string;
  content: string;
  modelLabel: string | null;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onClear: () => void;
  validation: JsonValidationResult;
};

export function JsonTrainingEditor({
  title,
  content,
  modelLabel,
  onTitleChange,
  onContentChange,
  onClear,
  validation,
}: JsonTrainingEditorProps) {
  function handleValidateClick() {
    validateTrainingJson(content);
  }

  function handlePrettyPrint() {
    const result = prettyPrintTrainingJson(content);
    if (result.ok) {
      onContentChange(result.formatted);
    }
  }

  return (
    <div className="space-y-4" data-testid="json-training-editor">
      <div className="space-y-1.5">
        <label htmlFor="training-json-title" className="text-sm font-medium text-zinc-800">
          JSON Title
        </label>
        <input
          id="training-json-title"
          data-testid="training-json-title"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="e.g. HS classification payload"
          className="w-full max-w-lg rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
      </div>

      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="training-json-content" className="text-sm font-medium text-zinc-800">
            JSON content
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="training-json-validate"
              onClick={handleValidateClick}
              className="text-xs font-medium text-indigo-700 underline-offset-2 hover:underline"
            >
              Validate JSON
            </button>
            <button
              type="button"
              data-testid="training-json-pretty-print"
              onClick={handlePrettyPrint}
              className="text-xs font-medium text-indigo-700 underline-offset-2 hover:underline"
            >
              Pretty print
            </button>
            <button
              type="button"
              data-testid="training-json-clear"
              onClick={onClear}
              className="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline"
            >
              Clear
            </button>
          </div>
        </div>
        <textarea
          id="training-json-content"
          data-testid="training-json-content"
          value={content}
          onChange={(event) => onContentChange(event.target.value)}
          rows={12}
          placeholder={JSON_TRAINING_PLACEHOLDER}
          spellCheck={false}
          className="w-full rounded-xl border border-zinc-200 px-3 py-3 font-mono text-sm leading-relaxed text-zinc-900 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
        <p className="text-xs text-zinc-500" data-testid="training-json-char-count">
          {content.length} characters
        </p>
      </div>

      <JsonValidationIndicator validation={validation} />

      <div
        className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700"
        data-testid="json-training-preview"
      >
        <p>
          <span className="font-medium text-zinc-800">JSON title:</span>{' '}
          {title.trim() || 'Untitled JSON training'}
        </p>
        <p className="mt-1">
          <span className="font-medium text-zinc-800">Model:</span>{' '}
          {modelLabel ?? 'Not selected'}
        </p>
        <p className="mt-1">
          <span className="font-medium text-zinc-800">Validation:</span>{' '}
          <span data-testid="json-preview-validation-status">{validationStatusLabel(validation)}</span>
        </p>
        <p className="mt-1">
          <span className="font-medium text-zinc-800">Characters:</span>{' '}
          {content.length}
        </p>
      </div>
    </div>
  );
}

function validationStatusLabel(validation: JsonValidationResult): string {
  if (validation.status === 'valid') {
    return 'Valid JSON';
  }
  if (validation.status === 'invalid') {
    return 'Invalid JSON';
  }
  return 'Empty';
}

function JsonValidationIndicator({ validation }: { validation: JsonValidationResult }) {
  if (validation.status === 'empty') {
    return (
      <p className="text-sm text-zinc-600" data-testid="json-validation-status" data-state="empty">
        Enter JSON to validate.
      </p>
    );
  }
  if (validation.status === 'invalid') {
    return (
      <p
        role="alert"
        data-testid="json-validation-status"
        data-state="invalid"
        className="text-sm text-red-600"
      >
        Invalid JSON: {validation.message}
      </p>
    );
  }
  return (
    <p
      data-testid="json-validation-status"
      data-state="valid"
      className="text-sm font-medium text-emerald-700"
    >
      Valid JSON
    </p>
  );
}
