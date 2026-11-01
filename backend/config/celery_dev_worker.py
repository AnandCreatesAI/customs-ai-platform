"""
Start/stop a Celery worker subprocess for local ``runserver`` only.

Uses a real Celery worker process (not threads). Production and other management
commands never import this module for side effects.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import IO, Any, TextIO

from django.conf import settings

logger = logging.getLogger(__name__)

_SHUTDOWN_GRACE_SECONDS = 10


def should_start_dev_celery_worker(*, use_reloader: bool) -> bool:
    if not getattr(settings, 'CELERY_AUTO_START_WORKER', False):
        return False
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        return False
    settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', '')
    if settings_module.endswith('.production'):
        return False
    if use_reloader and os.environ.get('RUN_MAIN') != 'true':
        return False
    return True


def _pid_file_path() -> Path:
    return Path(getattr(settings, 'CELERY_DEV_WORKER_PID_FILE', settings.BASE_DIR / '.celery-dev-worker.pid'))


def _broker_ping_ok() -> tuple[bool, str | None]:
    broker_url = settings.CELERY_BROKER_URL
    try:
        import redis
    except ImportError:
        return False, 'redis package is not installed (pip install redis).'

    try:
        client = redis.from_url(broker_url, socket_connect_timeout=3)
        client.ping()
    except Exception as exc:
        return False, f'Redis broker unreachable at {broker_url}: {exc}'
    return True, None


def _read_pid(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding='utf-8').strip()
        return int(raw)
    except (OSError, ValueError):
        return None


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def _terminate_pid(pid: int) -> None:
    if pid == os.getpid():
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return

    deadline = time.monotonic() + _SHUTDOWN_GRACE_SECONDS
    while time.monotonic() < deadline:
        if not _process_alive(pid):
            return
        time.sleep(0.2)

    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return


def _stop_stale_pidfile_worker(stdout: TextIO | IO[str] | None = None) -> None:
    path = _pid_file_path()
    if not path.is_file():
        return
    pid = _read_pid(path)
    path.unlink(missing_ok=True)
    if pid is None or not _process_alive(pid):
        return
    if pid == os.getpid():
        return
    _write_user(
        stdout,
        f'Stopping previous dev Celery worker (pid {pid}) before starting a new one.\n',
    )
    _terminate_pid(pid)


def _write_user(stream: TextIO | IO[str] | None, message: str) -> None:
    if stream is not None:
        stream.write(message)
        stream.flush()
    else:
        logger.info(message.rstrip())


def _worker_command() -> list[str]:
    loglevel = getattr(settings, 'CELERY_DEV_WORKER_LOGLEVEL', 'info')
    pool = getattr(settings, 'CELERY_DEV_WORKER_POOL', 'solo')
    concurrency = getattr(settings, 'CELERY_DEV_WORKER_CONCURRENCY', 1)
    hostname = getattr(settings, 'CELERY_DEV_WORKER_HOSTNAME', 'dev_runserver@%h')
    return [
        sys.executable,
        '-m',
        'celery',
        '-A',
        'config',
        'worker',
        f'--loglevel={loglevel}',
        f'--pool={pool}',
        f'--concurrency={concurrency}',
        f'--hostname={hostname}',
        '--without-gossip',
        '--without-mingle',
    ]


def start_dev_celery_worker(
    *,
    stdout: TextIO | IO[str] | None = None,
) -> subprocess.Popen[Any] | None:
    ok, err = _broker_ping_ok()
    if not ok:
        _write_user(
            stdout,
            f'Celery dev worker not started: {err}\n'
            'Training jobs will stay queued until Redis is available and a worker is running.\n'
            'Start Redis (e.g. docker compose up redis) or run: python manage.py check_celery_broker\n',
        )
        return None

    _stop_stale_pidfile_worker(stdout)

    cmd = _worker_command()
    _write_user(stdout, f'Starting Celery dev worker: {" ".join(cmd)}\n')

    proc = subprocess.Popen(
        cmd,
        cwd=str(settings.BASE_DIR),
        env=os.environ.copy(),
    )

    path = _pid_file_path()
    try:
        path.write_text(str(proc.pid), encoding='utf-8')
    except OSError as exc:
        _write_user(stdout, f'Warning: could not write Celery pid file {path}: {exc}\n')

    _write_user(stdout, f'Celery dev worker started (pid {proc.pid}).\n')
    return proc


def stop_dev_celery_worker(
    proc: subprocess.Popen[Any] | None,
    *,
    stdout: TextIO | IO[str] | None = None,
) -> None:
    path = _pid_file_path()
    if proc is None:
        return

    if proc.poll() is not None:
        path.unlink(missing_ok=True)
        return

    _write_user(stdout, f'Stopping Celery dev worker (pid {proc.pid})…\n')
    proc.terminate()
    try:
        proc.wait(timeout=_SHUTDOWN_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    path.unlink(missing_ok=True)
    _write_user(stdout, 'Celery dev worker stopped.\n')
