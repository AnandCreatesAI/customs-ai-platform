from __future__ import annotations

import os
import shutil
from pathlib import Path

from django.conf import settings

from apps.document_extraction.base import ExtractionError
from apps.document_extraction.conf import libreoffice_timeout_seconds
from apps.document_extraction.subprocess.runner import SubprocessError, run_allowlisted


def libreoffice_binary() -> str:
    return getattr(settings, 'EXTRACTION_LIBREOFFICE_BINARY', 'soffice')


def convert_to_format(
    input_path: Path,
    *,
    output_dir: Path,
    target_ext: str,
) -> Path:
    binary = libreoffice_binary()
    if shutil.which(binary) is None and not Path(binary).exists():
        raise ExtractionError('LibreOffice is not available for legacy document conversion.')

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        binary,
        '--headless',
        '--nologo',
        '--nofirststartwizard',
        '--convert-to',
        target_ext,
        '--outdir',
        str(output_dir),
        str(input_path),
    ]
    try:
        run_allowlisted(command, timeout=libreoffice_timeout_seconds(), cwd=str(output_dir))
    except SubprocessError as exc:
        raise ExtractionError(f'LibreOffice conversion failed: {exc.message}') from exc

    expected = output_dir / f'{input_path.stem}.{target_ext}'
    if not expected.exists():
        candidates = list(output_dir.glob(f'*.{target_ext}'))
        if not candidates:
            raise ExtractionError('LibreOffice conversion produced no output file.')
        expected = candidates[0]
    return expected


def convert_doc_to_docx(input_path: Path, output_dir: Path) -> Path:
    return convert_to_format(input_path, output_dir=output_dir, target_ext='docx')


def convert_xls_to_xlsx(input_path: Path, output_dir: Path) -> Path:
    return convert_to_format(input_path, output_dir=output_dir, target_ext='xlsx')
