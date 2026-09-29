from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Deprecated: Demo data seeding has been permanently disabled."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("seed_demo is deprecated and disabled. The system now uses ensure_admin to maintain the Dev Admin account."))
