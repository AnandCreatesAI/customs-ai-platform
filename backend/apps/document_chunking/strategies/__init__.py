from apps.document_chunking.registry.base import register_chunk_strategy
from apps.document_chunking.registry.profile import FormatProfile
from apps.document_chunking.strategies.json_records import JsonRecordsChunkStrategy
from apps.document_chunking.strategies.ocr import OcrChunkStrategy
from apps.document_chunking.strategies.prose import ProseChunkStrategy
from apps.document_chunking.strategies.spreadsheet import SpreadsheetChunkStrategy
from apps.document_chunking.strategies.table import TableChunkStrategy


def register_default_chunk_strategies() -> None:
    register_chunk_strategy(
        strategy=SpreadsheetChunkStrategy(),
        predicate=lambda profile: profile.has_sheets
        or profile.extractor_key in {'xlsx', 'xls', 'csv'},
        priority=10,
    )
    register_chunk_strategy(
        strategy=JsonRecordsChunkStrategy(),
        predicate=lambda profile: profile.has_json_paths or profile.extractor_key == 'json',
        priority=20,
    )
    register_chunk_strategy(
        strategy=TableChunkStrategy(),
        predicate=lambda profile: profile.has_tables,
        priority=30,
    )
    register_chunk_strategy(
        strategy=OcrChunkStrategy(),
        predicate=lambda profile: profile.has_ocr or profile.extractor_key == 'image',
        priority=40,
    )
    register_chunk_strategy(
        strategy=ProseChunkStrategy(),
        predicate=lambda _profile: True,
        priority=100,
    )
