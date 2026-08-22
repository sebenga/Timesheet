from django.core.management.base import BaseCommand

from tracker.bootstrap import ensure_admin_user
from tracker.models import TimeMarginSettings


class Command(BaseCommand):
    help = 'Create the Timeshit admin account and default margin settings.'

    def handle(self, *args, **options):
        user = ensure_admin_user()
        TimeMarginSettings.get_solo()
        self.stdout.write(self.style.SUCCESS(f'Admin ready: {user.username}'))
