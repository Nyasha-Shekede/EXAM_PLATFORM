"""Minimal Django email backend for Resend's HTTPS API (no SDK required)."""
import json
import logging
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        key = settings.RESEND_API_KEY
        if not key:
            raise RuntimeError("RESEND_API_KEY must be configured to send email")
        count = 0
        for message in email_messages:
            recipients = message.to
            if not recipients:
                continue
            data = {"from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": recipients, "subject": message.subject, "text": message.body}
            # Support HTML email content if present
            if hasattr(message, "alternatives"):
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        data["html"] = content
                        break
            if hasattr(message, "content_subtype") and message.content_subtype == "html":
                data["html"] = message.body

            if message.cc:
                data["cc"] = message.cc
            if message.bcc:
                data["bcc"] = message.bcc
            if message.reply_to:
                data["reply_to"] = message.reply_to
            # Resend accepts separate cc/bcc fields; never disclose BCC in the To list.
            request = Request("https://api.resend.com/emails", data=json.dumps(data).encode(),
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                              method="POST")
            try:
                with urlopen(request, timeout=8) as response:
                    response.read()
                count += 1
            except HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                logger.error("Resend API rejected email (HTTP %s): %s", e.code, err_body)
                if not self.fail_silently:
                    raise RuntimeError(f"Resend rejected email (HTTP {e.code}): {err_body}") from e
            except Exception:
                if not self.fail_silently:
                    raise
        return count

