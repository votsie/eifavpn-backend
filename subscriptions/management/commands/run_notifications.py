from django.core.management.base import BaseCommand
from subscriptions.notifications import run_subscription_notifications
from subscriptions.renewal import run_auto_renewal


class Command(BaseCommand):
    help = 'Run subscription notifications (expiry warnings, winback promos) and auto-renewal invoice generation'

    def handle(self, *args, **options):
        self.stdout.write('Running subscription notifications...')
        notif_stats = run_subscription_notifications()
        self.stdout.write(f'  Notifications: {notif_stats}')

        self.stdout.write('Running auto-renewal...')
        renewal_stats = run_auto_renewal()
        self.stdout.write(f'  Auto-renewal: {renewal_stats}')

        self.stdout.write(self.style.SUCCESS('Done.'))
