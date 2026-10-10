import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Ensure developer / superuser admin account exists based on environment variables"

    def handle(self, *args, **options):
        User = get_user_model()
        username = (os.getenv("DEV_ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME") or "admin").strip()
        email = (os.getenv("DEV_ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "admin@africadronekings.com").strip()
        password = (os.getenv("DEV_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or "ChangeMe-Admin-2026").strip()

        if not username:
            self.stdout.write(self.style.WARNING("DEV_ADMIN_USERNAME is empty. Skipping admin account setup."))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": "Dev",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
        )

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if password:
            user.set_password(password)
        user.save()  # <-- persist the account and password to DB

        # Completely nuke legacy demo seed records from the database
        from exams.models import Module, Exam
        Exam.objects.filter(code="DEMO-EXAM").delete()
        Module.objects.filter(code="DEMO").delete()
        User.objects.filter(username="DEMO001").delete()

        status_text = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(f"{status_text} superuser '{username}' ({email}). Legacy demo seed data purged."))
