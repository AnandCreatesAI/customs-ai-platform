from django.core.management.base import BaseCommand

from apps.vector_indexing.reconciliation import list_reconciliation_candidates, reconcile_indexing_run
from apps.vector_indexing.services import IndexingServiceError


class Command(BaseCommand):
    help = 'Reconcile Qdrant activation payloads with PostgreSQL DocumentIndexActivation.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-id',
            type=str,
            help='Reconcile a single indexing run UUID.',
        )
        parser.add_argument(
            '--all-candidates',
            action='store_true',
            help='Reconcile all runs returned by list_reconciliation_candidates().',
        )

    def handle(self, *args, **options):
        run_id = options.get('run_id')
        if run_id:
            self._reconcile_one(run_id)
            return
        if options['all_candidates']:
            candidates = list_reconciliation_candidates()
            self.stdout.write(f'Reconciling {len(candidates)} candidate run(s).')
            for candidate_id in candidates:
                self._reconcile_one(candidate_id)
            return
        candidates = list_reconciliation_candidates()
        self.stdout.write(f'Reconciliation candidates: {len(candidates)}')
        for candidate_id in candidates:
            self.stdout.write(f'  {candidate_id}')
        self.stdout.write('Pass --run-id=<uuid> or --all-candidates to reconcile.')

    def _reconcile_one(self, run_id: str) -> None:
        try:
            reconcile_indexing_run(run_id)
        except IndexingServiceError as exc:
            self.stderr.write(self.style.ERROR(f'{run_id}: {exc.message}'))
            return
        self.stdout.write(self.style.SUCCESS(f'Reconciled run {run_id}'))
