from django.core.management.base import BaseCommand
from markets.trendyol_app.tasks import schedule_batch_status_checks

class Command(BaseCommand):
    help = 'Checks status of all pending Trendyol batch requests'

    def handle(self, *args, **options):
        count = schedule_batch_status_checks()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully checked {count} batch requests')
        )