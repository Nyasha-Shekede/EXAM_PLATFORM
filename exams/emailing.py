"""Transactional messages. Never include raw passwords or answer keys."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def _send(user_id, subject, body, html_body=None):
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user or not user.email:
        return
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Could not deliver transactional email to user id %s", user_id)


def welcome(user, base_url, password_setup=False):
    """Send after commit; use a one-time password-set link, never a password."""
    user_id = user.pk

    def deliver():
        current = get_user_model().objects.filter(pk=user_id).first()
        if not current:
            return
        subject = f"Welcome to {settings.SITE_NAME}"
        ctx = {
            "user": current,
            "site_name": settings.SITE_NAME,
            "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
            "subject": subject,
        }
        if password_setup:
            uid = urlsafe_base64_encode(force_bytes(current.pk))
            token = default_token_generator.make_token(current)
            url = base_url + reverse("password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            ctx["action_url"] = url
            message = f"Welcome to {settings.SITE_NAME}. Your username is {current.username}. Set your password here: {url}"
            try:
                html = render_to_string("emails/welcome_password_setup.html", ctx)
            except Exception:
                html = None
        else:
            url = base_url + reverse("login")
            ctx["action_url"] = url
            message = f"Welcome to {settings.SITE_NAME}. Your username is {current.username}. Sign in here: {url}"
            try:
                html = render_to_string("emails/welcome_signup.html", ctx)
            except Exception:
                html = None
        _send(user_id, subject, message, html_body=html)

    transaction.on_commit(deliver)


def attempt_notice(attempt, event):
    user_id, attempt_id = attempt.candidate_id, attempt.pk

    def deliver():
        from .models import Attempt
        current = Attempt.objects.select_related("exam", "exam__module", "candidate").get(pk=attempt_id)
        subject = f"Exam attempt {event} · {settings.SITE_NAME}"
        render_host = getattr(settings, "RENDER_EXTERNAL_HOSTNAME", "")
        base_url = f"https://{render_host}" if render_host else ""

        ctx = {
            "user": current.candidate,
            "attempt": current,
            "exam": current.exam,
            "duration_minutes": current.exam.duration_minutes,
            "site_name": settings.SITE_NAME,
            "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
            "subject": subject,
        }
        if event == "started":
            ctx["action_url"] = f"{base_url}{reverse('dashboard')}" if base_url else reverse("dashboard")
            message = f"Your attempt for {current.exam.title} has started. Return to the academy to complete it."
            try:
                html = render_to_string("emails/attempt_started.html", ctx)
            except Exception:
                html = None
        else:
            ctx["action_url"] = f"{base_url}{reverse('result', kwargs={'attempt_id': current.pk})}" if base_url else reverse("result", kwargs={"attempt_id": current.pk})
            message = f"Your attempt for {current.exam.title} was received. View your result after signing in."
            try:
                html = render_to_string("emails/attempt_submitted.html", ctx)
            except Exception:
                html = None
        _send(user_id, subject, message, html_body=html)

    transaction.on_commit(deliver)

