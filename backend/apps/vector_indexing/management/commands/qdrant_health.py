from django.conf import settings
from django.core.management.base import BaseCommand

from gateways.qdrant.health import check_qdrant_health


class Command(BaseCommand):
    help = 'Check Qdrant connectivity (does not run at Django startup).'

    def handle(self, *args, **options):
        if not settings.QDRANT_INDEXING_ENABLED:
            self.stdout.write('Qdrant indexing is disabled (QDRANT_INDEXING_ENABLED=false).')
            return
        ok = check_qdrant_health()
        if ok:
            self.stdout.write(self.style.SUCCESS('Qdrant health check passed.'))
        else:
            self.stdout.write(self.style.ERROR('Qdrant health check failed.'))
