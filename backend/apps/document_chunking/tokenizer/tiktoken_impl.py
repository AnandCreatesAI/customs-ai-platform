from __future__ import annotations

import tiktoken

from apps.document_chunking.tokenizer.base import Tokenizer


class TiktokenTokenizer(Tokenizer):
    def __init__(self, encoding_name: str) -> None:
        self._encoding = tiktoken.get_encoding(encoding_name)
        self.encoding_name = encoding_name

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))

    def split_text(
        self,
        text: str,
        *,
        max_tokens: int,
        overlap_tokens: int = 0,
    ) -> list[str]:
        if not text or not text.strip():
            return []
        if max_tokens <= 0:
            raise ValueError('max_tokens must be positive')

        tokens = self._encoding.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        overlap = max(0, min(overlap_tokens, max_tokens - 1))
        step = max(1, max_tokens - overlap)
        parts: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            parts.append(self._encoding.decode(chunk_tokens))
            if end >= len(tokens):
                break
            start += step
        return parts
