from django.core.management.base import BaseCommand

from apps.vector_indexing.recovery import (
    list_reconciliation_candidates,
    recover_stale_indexing_runs,
    redispatch_queued_indexing_runs,
)


class Command(BaseCommand):
    help = 'Recover stale indexing runs and optionally redispatch queued runs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--redispatch',
            action='store_true',
            help='Redispatch queued indexing runs with dispatch errors.',
        )

    def handle(self, *args, **options):
        stale = recover_stale_indexing_runs()
        self.stdout.write(f'Stale indexing runs marked failed: {len(stale)}')
        if options['redispatch']:
            redispatched = redispatch_queued_indexing_runs(only_dispatch_errors=True)
            self.stdout.write(f'Redispatched indexing runs: {len(redispatched)}')
        reconcile = list_reconciliation_candidates()
        self.stdout.write(f'Reconciliation candidates: {len(reconcile)}')
        self.stdout.write('Run manage.py reconcile_indexing_runs --all-candidates to repair Qdrant payloads.')
