"""Transactional messages. Never include raw passwords or answer keys."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def _send(user_id, subject, body):
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user or not user.email:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:
        logger.exception("Could not deliver transactional email to user id %s", user_id)


def welcome(user, base_url, password_setup=False):
    """Send after commit; use a one-time password-set link, never a password."""
    user_id = user.pk

    def deliver():
        current = get_user_model().objects.filter(pk=user_id).first()
        if not current:
            return
        if password_setup:
            uid = urlsafe_base64_encode(force_bytes(current.pk))
            token = default_token_generator.make_token(current)
            url = base_url + reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            message = f"Welcome to {settings.SITE_NAME}. Your username is {current.username}. Set your password here: {url}"
        else:
            message = f"Welcome to {settings.SITE_NAME}. Your username is {current.username}. Sign in here: {base_url + reverse('login')}"
        _send(user_id, f"Welcome to {settings.SITE_NAME}", message)

    transaction.on_commit(deliver)


def attempt_notice(attempt, event):
    user_id, attempt_id = attempt.candidate_id, attempt.pk
    def deliver():
        from .models import Attempt
        current = Attempt.objects.select_related("exam").get(pk=attempt_id)
        if event == "started":
            message = f"Your attempt for {current.exam.title} has started. Return to the academy to complete it."
        else:
            message = f"Your attempt for {current.exam.title} was received. View your result after signing in."
        _send(user_id, f"Exam attempt {event} · {settings.SITE_NAME}", message)
    transaction.on_commit(deliver)
