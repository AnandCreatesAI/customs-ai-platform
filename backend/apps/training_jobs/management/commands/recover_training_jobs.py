from django.core.management.base import BaseCommand

from apps.training_jobs.worker_recovery import recover_stale_processing_jobs, redispatch_queued_jobs


class Command(BaseCommand):
    help = (
        'Recover training jobs after broker or worker outages: '
        'mark stale processing jobs failed and re-dispatch queued jobs with dispatch errors.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--stale',
            action='store_true',
            help='Mark stale processing jobs as failed (worker interruption recovery).',
        )
        parser.add_argument(
            '--redispatch',
            action='store_true',
            help='Re-dispatch queued jobs that have a dispatch_error recorded.',
        )
        parser.add_argument(
            '--all-queued',
            action='store_true',
            help='With --redispatch, include all queued jobs (not only dispatch_error rows).',
        )

    def handle(self, *args, **options):
        ran = False
        if options['stale']:
            ran = True
            stale = recover_stale_processing_jobs()
            self.stdout.write(
                self.style.SUCCESS(f'Marked {len(stale)} stale processing job(s) as failed.')
            )
            for job_id in stale:
                self.stdout.write(f'  stale_failed={job_id}')

        if options['redispatch']:
            ran = True
            only_errors = not options['all_queued']
            redispatched = redispatch_queued_jobs(only_dispatch_errors=only_errors)
            self.stdout.write(
                self.style.SUCCESS(f'Re-dispatched {len(redispatched)} queued job(s).')
            )
            for job_id in redispatched:
                self.stdout.write(f'  redispatched={job_id}')

        if not ran:
            self.stdout.write('Nothing to do. Pass --stale and/or --redispatch.')
