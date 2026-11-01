'use client';

import { displayFilename, type RagSourceReference } from '@/types/rag-types';

type MessageSourcesPanelProps = {
  sources: RagSourceReference[];
  activeRef: number | null;
  onSelectSource: (ref: number) => void;
};

export function MessageSourcesPanel({
  sources,
  activeRef,
  onSelectSource,
}: MessageSourcesPanelProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="message-sources-panel"
      className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50/80 px-3 py-2"
    >
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        Sources
      </p>
      <ul className="space-y-1.5">
        {sources.map((source) => {
          const isActive = activeRef === source.ref;
          const filename = displayFilename(source);
          return (
            <li key={`${source.ref}-${source.chunk_id}`}>
              <button
                type="button"
                data-testid={`message-source-${source.ref}`}
                aria-label={`Source ${source.ref}: ${filename}`}
                aria-pressed={isActive}
                onClick={() => onSelectSource(source.ref)}
                className={`w-full rounded-lg px-2 py-1.5 text-left text-xs transition-colors ${
                  isActive
                    ? 'bg-white ring-1 ring-zinc-300'
                    : 'hover:bg-white/80'
                }`}
              >
                <span className="font-semibold text-zinc-800">[{source.ref}]</span>{' '}
                <span className="text-zinc-700">{filename}</span>
                {typeof source.chunk_index === 'number' ? (
                  <span className="text-zinc-500"> · chunk {source.chunk_index}</span>
                ) : null}
                {typeof source.score === 'number' && source.score > 0 ? (
                  <span className="text-zinc-500"> · score {source.score.toFixed(2)}</span>
                ) : null}
                {typeof source.artifact_version === 'number' && source.artifact_version > 0 ? (
                  <span className="text-zinc-500"> · v{source.artifact_version}</span>
                ) : null}
              </button>
              {isActive ? (
                <div
                  data-testid={`message-source-detail-${source.ref}`}
                  className="mt-1 rounded-lg border border-zinc-200 bg-white px-2 py-2 text-[11px] leading-relaxed text-zinc-600"
                >
                  <p>
                    Reference [{source.ref}] — metadata from your indexed knowledge base. Full
                    document text is not shown here.
                  </p>
                  <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
                    <dt className="text-zinc-500">Chunk</dt>
                    <dd className="truncate font-mono text-zinc-700">{source.chunk_id}</dd>
                    <dt className="text-zinc-500">Document</dt>
                    <dd className="truncate font-mono text-zinc-700">{source.document_id}</dd>
                  </dl>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
