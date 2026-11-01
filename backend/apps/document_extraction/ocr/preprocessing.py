from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


def preprocess_image_for_ocr(path: Path) -> Image.Image:
    with Image.open(path) as image:
        converted = ImageOps.exif_transpose(image)
        gray = ImageOps.grayscale(converted)
        return gray
