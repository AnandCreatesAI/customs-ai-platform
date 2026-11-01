from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def registered_training_task_names(celery_app) -> list[str]:
    """
    Return custom training task names registered on the Celery app.

    ``autodiscover_tasks()`` runs when ``config.celery`` is first imported, often
    before Django has finished loading installed apps, so task modules may not be
    imported yet. Re-run discovery with ``force=True`` and match on ``Task.name``
    (what ``celery inspect registered`` reports), not only registry dict keys.
    """
    celery_app.autodiscover_tasks(force=True)
    return sorted(
        task.name
        for task in celery_app.tasks.values()
        if getattr(task, 'name', '').startswith('training_jobs.')
    )


class Command(BaseCommand):
    help = 'Verify Redis broker connectivity for Celery (does not start workers).'

    def handle(self, *args, **options):
        broker_url = settings.CELERY_BROKER_URL
        self.stdout.write(f'Broker URL: {broker_url}')

        try:
            import redis
        except ImportError as exc:
            raise CommandError('redis package is not installed.') from exc

        try:
            client = redis.from_url(broker_url, socket_connect_timeout=3)
            client.ping()
        except Exception as exc:
            raise CommandError(f'Redis broker unreachable: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Redis broker ping OK.'))

        try:
            from config.celery import app
        except ImportError as exc:
            raise CommandError(f'Celery app import failed: {exc}') from exc

        registered = registered_training_task_names(app)
        self.stdout.write(f'Registered training tasks: {", ".join(registered) or "(none)"}')
