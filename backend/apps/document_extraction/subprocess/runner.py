from __future__ import annotations

import os
import subprocess
from typing import Mapping

ALLOWED_COMMANDS = frozenset({'soffice', 'libreoffice', 'tesseract'})


class SubprocessError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def sanitized_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env.keys()):
        upper = key.upper()
        if any(token in upper for token in ('KEY', 'SECRET', 'TOKEN', 'PASSWORD')):
            env.pop(key, None)
    return env


def run_allowlisted(
    command: list[str],
    *,
    timeout: int,
    cwd: str | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not command:
        raise SubprocessError('Empty command.')
    binary = os.path.basename(command[0])
    if binary not in ALLOWED_COMMANDS:
        raise SubprocessError(f'Command not allowlisted: {binary}')
    env = sanitized_env()
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SubprocessError(f'Command timed out after {timeout}s.') from exc
    except subprocess.CalledProcessError as exc:
        raise SubprocessError(f'Command failed with exit code {exc.returncode}.') from exc
