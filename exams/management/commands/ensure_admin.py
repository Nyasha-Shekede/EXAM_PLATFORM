"""One-time, explicit bootstrap. Never reset/promote an existing account on restart."""
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create an administrator only when explicit bootstrap credentials are supplied."

    @transaction.atomic
    def handle(self, *args, **options):
        username = (os.getenv("ADMIN_USERNAME") or os.getenv("DEV_ADMIN_USERNAME") or "").strip()
        password = os.getenv("ADMIN_PASSWORD") or os.getenv("DEV_ADMIN_PASSWORD") or ""
        email = (os.getenv("ADMIN_EMAIL") or os.getenv("DEV_ADMIN_EMAIL") or "").strip()
        if not username and not password:
            self.stdout.write("No bootstrap credentials configured; skipping admin creation.")
            return
        if not username or not password:
            raise CommandError("Supply both ADMIN_USERNAME and ADMIN_PASSWORD, or remove both.")
        User = get_user_model()
        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            if not existing.is_staff or not existing.is_superuser:
                raise CommandError("Bootstrap username belongs to a non-administrator. Choose a different username.")
            self.stdout.write("Administrator already exists; password, status and profile unchanged.")
            return
        user = User(username=username, email=email, is_staff=True, is_superuser=True, is_active=True)
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("Invalid bootstrap account: " + "; ".join(exc.messages)) from exc
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Created administrator '{username}'. Remove bootstrap password from the service environment."))
