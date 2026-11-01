from __future__ import annotations

from django.conf import settings

from apps.document_chunking.tokenizer.base import Tokenizer
from apps.document_chunking.tokenizer.tiktoken_impl import TiktokenTokenizer


def get_tokenizer() -> Tokenizer:
    provider = settings.CHUNKING_TOKENIZER_PROVIDER
    if provider == 'tiktoken':
        return TiktokenTokenizer(settings.CHUNKING_TOKENIZER_ENCODING)
    raise ValueError(f'Unsupported tokenizer provider: {provider}')
