from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from django_redsys.notifications.models import Notification


class Command(BaseCommand):
    help = 'Deletes the RedSys notifications first received more than DAYS days ago.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than', type=int, required=True, metavar='DAYS')

    def handle(self, *args, older_than, **options):
        if older_than < 0:
            raise CommandError('--older-than must be 0 or more days.')
        cutoff = timezone.now() - timedelta(days=older_than)
        deleted, _ = Notification.objects.filter(received_at__lt=cutoff).delete()
        self.stdout.write(f'{deleted} notifications deleted.')
