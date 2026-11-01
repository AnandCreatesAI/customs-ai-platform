from apps.document_extraction.extractors.csv import CsvExtractor
from apps.document_extraction.extractors.doc import DocExtractor
from apps.document_extraction.extractors.docx import DocxExtractor
from apps.document_extraction.extractors.image import ImageExtractor
from apps.document_extraction.extractors.json import JsonExtractor
from apps.document_extraction.extractors.pdf import PdfExtractor
from apps.document_extraction.extractors.txt import TxtExtractor
from apps.document_extraction.extractors.xls import XlsExtractor
from apps.document_extraction.extractors.xlsx import XlsxExtractor
from apps.document_extraction.registry import register_extractor

for _extractor in (
    TxtExtractor(),
    JsonExtractor(),
    CsvExtractor(),
    DocxExtractor(),
    XlsxExtractor(),
    DocExtractor(),
    XlsExtractor(),
    PdfExtractor(),
    ImageExtractor(),
):
    register_extractor(_extractor)
