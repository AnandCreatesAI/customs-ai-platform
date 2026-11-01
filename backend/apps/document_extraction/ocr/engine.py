from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apps.document_extraction.conf import ocr_language, ocr_timeout_seconds, use_mock_ocr
from apps.document_extraction.ocr.confidence import average_confidence
from apps.document_extraction.ocr.preprocessing import preprocess_image_for_ocr


@dataclass(frozen=True)
class OcrBlock:
    text: str
    confidence: float | None
    bbox: list[float] | None


def run_ocr_on_image(image_path: Path) -> list[OcrBlock]:
    if use_mock_ocr():
        return [OcrBlock(text='MOCK OCR TEXT', confidence=0.99, bbox=[0, 0, 100, 20])]

    try:
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise RuntimeError('pytesseract is not installed.') from exc

    image = preprocess_image_for_ocr(image_path)
    try:
        data = pytesseract.image_to_data(
            image,
            lang=ocr_language(),
            output_type=Output.DICT,
            timeout=ocr_timeout_seconds(),
        )
    except Exception as exc:
        raise RuntimeError('OCR engine failed.') from exc

    blocks: list[OcrBlock] = []
    n = len(data.get('text', []))
    for i in range(n):
        text = (data['text'][i] or '').strip()
        if not text:
            continue
        try:
            conf = float(data['conf'][i])
        except (TypeError, ValueError):
            conf = None
        if conf is not None and conf < 0:
            conf = None
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        blocks.append(OcrBlock(text=text, confidence=conf, bbox=[float(x), float(y), float(x + w), float(y + h)]))
    return blocks


def ocr_image_to_text(image_path: Path) -> tuple[str, float | None]:
    blocks = run_ocr_on_image(image_path)
    if not blocks:
        return '', None
    text = ' '.join(block.text for block in blocks)
    scores = [b.confidence for b in blocks if b.confidence is not None]
    return text, average_confidence(scores)
