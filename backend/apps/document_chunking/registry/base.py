from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from apps.document_chunking.chunk_types import ChunkDraft
from apps.document_chunking.config import ChunkingConfig
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_extraction.schema.types import Element


class ChunkStrategy(Protocol):
    name: str

    def matches(self, profile: FormatProfile) -> bool:
        ...

    def select_element_ids(
        self,
        profile: FormatProfile,
        elements: list[Element],
        assigned: set[str],
    ) -> list[Element]:
        ...

    def chunk(
        self,
        *,
        profile: FormatProfile,
        elements: list[Element],
        config: ChunkingConfig,
        tokenizer,
        start_index: int,
    ) -> tuple[list[ChunkDraft], int]:
        ...


@dataclass
class _RegisteredStrategy:
    priority: int
    predicate: Callable[[FormatProfile], bool]
    strategy: ChunkStrategy


_STRATEGIES: list[_RegisteredStrategy] = []


def register_chunk_strategy(
    *,
    strategy: ChunkStrategy,
    predicate: Callable[[FormatProfile], bool],
    priority: int,
) -> None:
    for entry in _STRATEGIES:
        if entry.strategy.name == strategy.name:
            raise ValueError(f'Chunk strategy already registered: {strategy.name}')
    _STRATEGIES.append(
        _RegisteredStrategy(priority=priority, predicate=predicate, strategy=strategy)
    )
    _STRATEGIES.sort(key=lambda item: item.priority)


def resolve_strategies(profile: FormatProfile) -> list[ChunkStrategy]:
    resolved: list[ChunkStrategy] = []
    for entry in _STRATEGIES:
        if entry.predicate(profile):
            resolved.append(entry.strategy)
    return resolved


def registered_strategy_names() -> list[str]:
    return [entry.strategy.name for entry in _STRATEGIES]
