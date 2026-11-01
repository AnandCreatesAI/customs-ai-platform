'use client';

import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';

import { splitContentWithCitations } from '@/lib/dashboard/citation-segment-parser';
import { sourcesByRef, type RagSourceReference } from '@/types/rag-types';

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code ?? []), 'className'],
    span: [...(defaultSchema.attributes?.span ?? []), 'className'],
    a: [...(defaultSchema.attributes?.a ?? []), 'href', 'title', 'rel', 'target'],
  },
};

const markdownComponents: Components = {
  a: ({ href, children, ...props }) => (
    <a
      {...props}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-2 hover:decoration-zinc-500"
    >
      {children}
    </a>
  ),
  p: ({ children, ...props }) => (
    <p {...props} className="my-3 first:mt-0 last:mb-0">
      {children}
    </p>
  ),
  ul: ({ children, ...props }) => (
    <ul {...props} className="my-3 list-disc space-y-1 pl-5">
      {children}
    </ul>
  ),
  ol: ({ children, ...props }) => (
    <ol {...props} className="my-3 list-decimal space-y-1 pl-5">
      {children}
    </ol>
  ),
  li: ({ children, ...props }) => (
    <li {...props} className="leading-7">
      {children}
    </li>
  ),
  h1: ({ children, ...props }) => (
    <h1 {...props} className="mt-4 mb-2 text-xl font-semibold text-zinc-900">
      {children}
    </h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 {...props} className="mt-4 mb-2 text-lg font-semibold text-zinc-900">
      {children}
    </h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 {...props} className="mt-3 mb-2 text-base font-semibold text-zinc-900">
      {children}
    </h3>
  ),
  table: ({ children, ...props }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-zinc-200">
      <table {...props} className="min-w-full border-collapse text-left text-sm">
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }) => (
    <th {...props} className="border-b border-zinc-200 bg-zinc-50 px-3 py-2 font-semibold">
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td {...props} className="border-b border-zinc-100 px-3 py-2 align-top">
      {children}
    </td>
  ),
  pre: ({ children, ...props }) => (
    <pre
      {...props}
      className="my-3 overflow-x-auto rounded-xl bg-zinc-950 px-4 py-3 text-[13px] leading-relaxed text-zinc-100"
    >
      {children}
    </pre>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className);
    if (isBlock) {
      return (
        <code {...props} className={className}>
          {children}
        </code>
      );
    }
    return (
      <code
        {...props}
        className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-[0.85em] text-zinc-800"
      >
        {children}
      </code>
    );
  },
  blockquote: ({ children, ...props }) => (
    <blockquote
      {...props}
      className="my-3 border-l-4 border-zinc-300 pl-4 text-zinc-600 italic"
    >
      {children}
    </blockquote>
  ),
};

type AssistantMarkdownProps = {
  content: string;
  sources?: RagSourceReference[];
  activeSourceRef?: number | null;
  onCitationClick?: (ref: number) => void;
};

function MarkdownChunk({ value }: { value: string }) {
  if (!value) {
    return null;
  }
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[[rehypeSanitize, sanitizeSchema], rehypeHighlight]}
      components={markdownComponents}
    >
      {value}
    </ReactMarkdown>
  );
}

export function AssistantMarkdown({
  content,
  sources = [],
  activeSourceRef = null,
  onCitationClick,
}: AssistantMarkdownProps) {
  const refMap = sourcesByRef(sources);
  const validRefs = new Set(refMap.keys());
  const segments = splitContentWithCitations(content, validRefs);

  return (
    <div
      data-testid="assistant-markdown"
      className="assistant-markdown max-w-none text-[15px] leading-7 text-zinc-800"
    >
      {segments.map((segment, index) => {
        if (segment.kind === 'text') {
          return <MarkdownChunk key={`text-${index}`} value={segment.value} />;
        }
        if (!segment.known) {
          return (
            <span key={`cite-${index}`} className="font-medium text-zinc-800">
              {segment.literal}
            </span>
          );
        }
        const isActive = activeSourceRef === segment.ref;
        return (
          <button
            key={`cite-${index}`}
            type="button"
            data-testid={`citation-ref-${segment.ref}`}
            aria-label={`Open source ${segment.ref}`}
            aria-pressed={isActive}
            onClick={() => onCitationClick?.(segment.ref)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onCitationClick?.(segment.ref);
              }
            }}
            className={`mx-0.5 inline align-baseline rounded px-0.5 text-[0.92em] font-semibold text-sky-800 underline decoration-sky-300 underline-offset-2 hover:bg-sky-50 hover:decoration-sky-600 ${
              isActive ? 'bg-sky-100 ring-1 ring-sky-200' : ''
            }`}
          >
            {segment.literal}
          </button>
        );
      })}
    </div>
  );
}
