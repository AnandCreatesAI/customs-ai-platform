from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from django.conf import settings


def workspace_root() -> Path:
    configured = getattr(settings, 'EXTRACTION_TEMP_ROOT', '')
    if configured:
        root = Path(configured)
    else:
        root = Path(settings.BASE_DIR).parent / 'var' / 'extraction_temp'
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def job_workspace(job_id: str) -> Iterator[Path]:
    path = workspace_root() / str(job_id)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@contextmanager
def temporary_subdir(parent: Path, prefix: str = 'work') -> Iterator[Path]:
    created = tempfile.mkdtemp(prefix=f'{prefix}-', dir=str(parent))
    sub = Path(created)
    os.chmod(sub, 0o700)
    try:
        yield sub
    finally:
        shutil.rmtree(sub, ignore_errors=True)
