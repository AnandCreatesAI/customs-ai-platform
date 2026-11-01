from __future__ import annotations

from abc import ABC, abstractmethod


class Tokenizer(ABC):
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def split_text(
        self,
        text: str,
        *,
        max_tokens: int,
        overlap_tokens: int = 0,
    ) -> list[str]:
        raise NotImplementedError
