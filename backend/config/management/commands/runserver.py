"""
Development runserver that optionally starts a Celery worker subprocess.

Overrides Daphne's ASGI runserver (first in INSTALLED_APPS) so ``python manage.py runserver``
still serves Channels/Daphne while auto-starting Celery locally.
"""

from __future__ import annotations

from daphne.management.commands.runserver import Command as DaphneRunserverCommand

from config.celery_dev_worker import (
    should_start_dev_celery_worker,
    start_dev_celery_worker,
    stop_dev_celery_worker,
)


class Command(DaphneRunserverCommand):
    def inner_run(self, *args, **options):
        use_reloader = options['use_reloader']
        start_worker = should_start_dev_celery_worker(use_reloader=use_reloader)
        worker_proc = None

        try:
            if start_worker:
                worker_proc = start_dev_celery_worker(stdout=self.stdout)
            return super().inner_run(*args, **options)
        finally:
            if start_worker:
                stop_dev_celery_worker(worker_proc, stdout=self.stdout)
