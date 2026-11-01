export type CitationSegment =
  | { kind: 'text'; value: string }
  | { kind: 'citation'; ref: number; literal: string; known: boolean };

type MarkdownRegion = {
  isProtected: boolean;
  value: string;
};

/** Markdown links with numeric labels, e.g. [1](https://example.com) */
const NUMERIC_MARKDOWN_LINK_PATTERN = /\[(\d+)\]\(([^)]*)\)/g;
const STANDALONE_CITATION_PATTERN = /\[(\d+)\](?!\()/g;

/**
 * Split content into prose vs protected (fenced / inline code) regions.
 * Unclosed ``` fences treat remainder of string as protected.
 */
export function extractMarkdownRegions(content: string): MarkdownRegion[] {
  if (!content) {
    return [];
  }

  const regions: MarkdownRegion[] = [];
  let cursor = 0;

  while (cursor < content.length) {
    const fenceStart = content.indexOf('```', cursor);
    const inlineStart = content.indexOf('`', cursor);

    let nextSpecial = -1;
    let kind: 'fence' | 'inline' | null = null;

    if (fenceStart !== -1 && (inlineStart === -1 || fenceStart <= inlineStart)) {
      nextSpecial = fenceStart;
      kind = 'fence';
    } else if (inlineStart !== -1) {
      nextSpecial = inlineStart;
      kind = 'inline';
    }

    if (nextSpecial === -1 || kind === null) {
      regions.push({ isProtected: false, value: content.slice(cursor) });
      break;
    }

    if (nextSpecial > cursor) {
      regions.push({ isProtected: false, value: content.slice(cursor, nextSpecial) });
    }

    if (kind === 'fence') {
      const fenceEnd = content.indexOf('```', nextSpecial + 3);
      if (fenceEnd === -1) {
        regions.push({ isProtected: true, value: content.slice(nextSpecial) });
        break;
      }
      regions.push({ isProtected: true, value: content.slice(nextSpecial, fenceEnd + 3) });
      cursor = fenceEnd + 3;
      continue;
    }

    const inlineEnd = content.indexOf('`', nextSpecial + 1);
    if (inlineEnd === -1) {
      regions.push({ isProtected: false, value: content.slice(nextSpecial) });
      break;
    }
    regions.push({ isProtected: true, value: content.slice(nextSpecial, inlineEnd + 1) });
    cursor = inlineEnd + 1;
  }

  return regions.filter((region) => region.value.length > 0);
}

function splitProseWithCitations(
  prose: string,
  validRefs: ReadonlySet<number>,
): CitationSegment[] {
  const segments: CitationSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  NUMERIC_MARKDOWN_LINK_PATTERN.lastIndex = 0;
  while ((match = NUMERIC_MARKDOWN_LINK_PATTERN.exec(prose)) !== null) {
    appendStandaloneCitations(prose.slice(lastIndex, match.index), validRefs, segments);
    segments.push({ kind: 'text', value: match[0] });
    lastIndex = NUMERIC_MARKDOWN_LINK_PATTERN.lastIndex;
  }
  appendStandaloneCitations(prose.slice(lastIndex), validRefs, segments);
  return segments;
}

function appendStandaloneCitations(
  prose: string,
  validRefs: ReadonlySet<number>,
  segments: CitationSegment[],
) {
  if (!prose) {
    return;
  }

  let textStart = 0;
  STANDALONE_CITATION_PATTERN.lastIndex = 0;
  let citationMatch: RegExpExecArray | null;
  while ((citationMatch = STANDALONE_CITATION_PATTERN.exec(prose)) !== null) {
    const before = prose.slice(textStart, citationMatch.index);
    if (before) {
      segments.push({ kind: 'text', value: before });
    }
    const ref = Number.parseInt(citationMatch[1] ?? '', 10);
    segments.push({
      kind: 'citation',
      ref,
      literal: citationMatch[0],
      known: validRefs.has(ref),
    });
    textStart = STANDALONE_CITATION_PATTERN.lastIndex;
  }
  const tail = prose.slice(textStart);
  if (tail) {
    segments.push({ kind: 'text', value: tail });
  }
}

/**
 * Split assistant answer text into markdown text runs and [n] citation tokens.
 * Code regions stay plain text. Standalone [n] are citations; [n](url) stays markdown.
 */
export function splitContentWithCitations(
  content: string,
  validRefs: ReadonlySet<number>,
): CitationSegment[] {
  const regions = extractMarkdownRegions(content);
  if (regions.length === 0) {
    return splitProseWithCitations(content, validRefs);
  }

  const segments: CitationSegment[] = [];
  for (const region of regions) {
    if (region.isProtected) {
      segments.push({ kind: 'text', value: region.value });
      continue;
    }
    segments.push(...splitProseWithCitations(region.value, validRefs));
  }
  return segments;
}
