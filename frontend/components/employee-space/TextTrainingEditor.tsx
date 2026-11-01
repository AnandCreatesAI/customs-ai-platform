'use client';

type TextTrainingEditorProps = {
  title: string;
  content: string;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onClear: () => void;
  errorMessage?: string | null;
};

export function TextTrainingEditor({
  title,
  content,
  onTitleChange,
  onContentChange,
  onClear,
  errorMessage,
}: TextTrainingEditorProps) {
  return (
    <div className="space-y-4" data-testid="text-training-editor">
      <div className="space-y-1.5">
        <label htmlFor="training-text-title" className="text-sm font-medium text-zinc-800">
          Text Title
        </label>
        <input
          id="training-text-title"
          data-testid="training-text-title"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="e.g. Customs clearance FAQ"
          className="w-full max-w-lg rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-900 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
      </div>
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <label htmlFor="training-text-content" className="text-sm font-medium text-zinc-800">
            Training text
          </label>
          <button
            type="button"
            data-testid="training-text-clear"
            onClick={onClear}
            className="text-xs font-medium text-zinc-600 underline-offset-2 hover:text-zinc-900 hover:underline"
          >
            Clear text
          </button>
        </div>
        <textarea
          id="training-text-content"
          data-testid="training-text-content"
          value={content}
          onChange={(event) => onContentChange(event.target.value)}
          rows={10}
          placeholder="Paste training content here…"
          className="w-full rounded-xl border border-zinc-200 px-3 py-3 text-sm leading-relaxed text-zinc-900 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-200"
        />
        <p className="text-xs text-zinc-500" data-testid="training-text-char-count">
          {content.length} characters
        </p>
      </div>
      {errorMessage ? (
        <p role="alert" data-testid="text-training-error" className="text-sm text-red-600">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
