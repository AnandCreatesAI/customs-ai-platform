from django.core.management.base import BaseCommand

from apps.model_management.models import BusinessModel, BusinessModelKey

SEED_BUSINESS_MODELS = (
    {'key': BusinessModelKey.USER, 'name': 'User Model'},
    {'key': BusinessModelKey.EBOOKS, 'name': 'eBooks Model'},
    {'key': BusinessModelKey.EMPLOYEE, 'name': 'Employee Model'},
    {'key': BusinessModelKey.HS_CODE, 'name': 'HS Code Model'},
)


class Command(BaseCommand):
    help = 'Seed platform business model definitions (idempotent).'

    def handle(self, *args, **options):
        created_count = 0
        for entry in SEED_BUSINESS_MODELS:
            _, created = BusinessModel.objects.get_or_create(
                key=entry['key'],
                defaults={
                    'name': entry['name'],
                    'description': '',
                    'is_active': True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Seed complete: {created_count} created, '
                f'{len(SEED_BUSINESS_MODELS) - created_count} already present.'
            )
        )
