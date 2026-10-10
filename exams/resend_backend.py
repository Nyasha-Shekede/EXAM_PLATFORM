"""Minimal Django email backend for Resend's HTTPS API (no SDK required)."""
import json
from urllib.request import Request, urlopen
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


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
            except Exception:
                if not self.fail_silently:
                    raise
        return count
