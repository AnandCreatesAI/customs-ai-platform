from __future__ import annotations

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.exceptions import NoChunkStrategyError, UnsupportedFormatError
from apps.document_chunking.registry.base import resolve_strategies
from apps.document_chunking.registry.profile import FormatProfile, build_format_profile
from apps.document_extraction.registry import registered_extractor_keys
from apps.document_extraction.schema.types import ExtractionBundle, Element


_CHUNKABLE_KINDS = frozenset(
    {
        'heading',
        'paragraph',
        'list_item',
        'table',
        'table_row',
        'table_cell',
        'sheet',
        'sheet_row',
        'field',
        'json_value',
        'ocr_block',
        'vision_block',
    }
)


def _has_chunkable_content(elements: list[Element]) -> bool:
    for element in elements:
        if element.kind in _CHUNKABLE_KINDS:
            text = (element.normalized_text or element.text or '').strip()
            if text:
                return True
            if element.structured_data:
                return True
        if element.kind == 'sheet_row':
            return True
    return False


def generate_chunks(
    bundle: ExtractionBundle,
    *,
    config: ChunkingConfig,
    tokenizer,
) -> list[ChunkDraft]:
    extractor_key = bundle.pipeline.extractor_key
    if extractor_key not in registered_extractor_keys():
        raise UnsupportedFormatError(
            f'No extraction adapter registered for extractor key {extractor_key!r}. '
            'Register a Phase 3 extractor before chunking.'
        )

    if not bundle.elements:
        raise NoChunkStrategyError('Extraction artifact contains no elements to chunk.')

    if not _has_chunkable_content(bundle.elements):
        raise NoChunkStrategyError('Extraction artifact has no chunkable content.')

    profile = build_format_profile(bundle)
    strategies = resolve_strategies(profile)
    if not strategies:
        raise NoChunkStrategyError(
            f'No chunk strategy registered for extractor {extractor_key!r}. '
            'Register a Phase 4 chunk adapter for this format.'
        )

    assigned: set[str] = set()
    all_chunks: list[ChunkDraft] = []
    next_index = 0

    for strategy in strategies:
        selected = strategy.select_element_ids(profile, bundle.elements, assigned)
        if not selected:
            continue
        chunks, next_index = strategy.chunk(
            profile=profile,
            elements=selected,
            config=config,
            tokenizer=tokenizer,
            start_index=next_index,
        )
        all_chunks.extend(chunks)

    unassigned = [
        element
        for element in bundle.elements
        if element.element_id not in assigned and element.kind not in {'image_ref', 'sheet'}
    ]
    if unassigned and not all_chunks:
        raise NoChunkStrategyError(
            'Unable to chunk extracted elements with registered strategies. '
            f'Unassigned element kinds: {sorted({el.kind for el in unassigned})}.'
        )

    if config.max_chunks_per_document > 0 and len(all_chunks) > config.max_chunks_per_document:
        raise UnsupportedFormatError(
            f'Document produced {len(all_chunks)} chunks, exceeding the configured safety limit '
            f'{config.max_chunks_per_document}.'
        )

    if not all_chunks:
        raise NoChunkStrategyError('Chunking produced zero chunks.')

    for index, chunk in enumerate(all_chunks):
        chunk.chunk_index = index
    return all_chunks
