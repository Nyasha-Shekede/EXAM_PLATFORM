import json
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import Enrollment, Lesson, Module
from .services import start_attempt, submit_attempt
from .tests import Base


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LearningTests(TestCase):
    def setUp(self):
        self.teacher = get_user_model().objects.create_user("teacher", password="Strong-pass-222", is_staff=True)
        self.other_teacher = get_user_model().objects.create_user("other_teacher", password="Strong-pass-222", is_staff=True)
        self.student = get_user_model().objects.create_user("student", "student@example.test", "Strong-pass-222")
        self.module = Module.objects.create(code="FLIGHT", title="Flight skills", instructor=self.teacher,
                                            description="Learn how to plan a flight")
        self.draft = Lesson.objects.create(module=self.module, title="Unpublished", content="Secret", published=False)
        self.lesson = Lesson.objects.create(module=self.module, title="Preparation", content="Prepare safely", published=True)

    def test_signup_is_student_and_sends_welcome_without_password(self):
        self.client.logout()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("signup"), {"username": "newpilot", "email": "new@example.test",
                 "password1": "Strong-pass-838", "password2": "Strong-pass-838"})
        self.assertRedirects(response, reverse("module_catalog"))
        created = get_user_model().objects.get(username="newpilot")
        self.assertFalse(created.is_staff)
        self.assertEqual(created.email, "new@example.test")
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Strong-pass-838", mail.outbox[0].body)
        self.client.logout()
        response = self.client.post(reverse("signup"), {"username": "newpilot2", "email": "NEW@example.test",
                 "password1": "Strong-pass-838", "password2": "Strong-pass-838"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already uses this email")

    def test_enrollment_and_published_lesson_access(self):
        self.client.force_login(self.student)
        link = reverse("lesson_detail", args=[self.module.pk, self.lesson.pk])
        self.assertEqual(self.client.get(link).status_code, 404)
        self.assertEqual(self.client.get(reverse("module_detail", args=[self.module.pk])).status_code, 200)
        self.client.post(reverse("enroll", args=[self.module.pk]))
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertContains(self.client.get(link), "Prepare safely")
        self.assertEqual(self.client.get(reverse("lesson_detail", args=[self.module.pk, self.draft.pk])).status_code, 404)
        self.client.post(reverse("enroll", args=[self.module.pk]))
        self.assertEqual(Enrollment.objects.count(), 1)
        self.module.active = False
        self.module.save()
        self.assertEqual(self.client.get(link).status_code, 404)

    def test_instructor_can_author_but_other_staff_cannot_edit(self):
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(reverse("lesson_edit", args=[self.module.pk, self.lesson.pk])).status_code, 404)
        self.client.force_login(self.teacher)
        response = self.client.post(reverse("lesson_create", args=[self.module.pk]),
                      {"title": "Weather", "content": "Clouds", "position": 2, "published": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Lesson.objects.filter(module=self.module, title="Weather", published=True).exists())

    def test_unlisted_module_visible_only_to_its_author(self):
        self.module.active = False
        self.module.save()
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get(reverse("module_catalog")), "Flight skills")
        self.client.force_login(self.other_teacher)
        self.assertNotContains(self.client.get(reverse("module_catalog")), "Flight skills")
        self.assertEqual(self.client.get(reverse("module_detail", args=[self.module.pk])).status_code, 404)

    def test_attachment_is_private_and_requires_enrollment(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.lesson.attachment.save("guide.txt", SimpleUploadedFile("guide.txt", b"private"), save=True)
            url = reverse("lesson_attachment", args=[self.module.pk, self.lesson.pk])
            self.client.force_login(self.student)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.post(reverse("enroll", args=[self.module.pk]))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"private")
            self.assertIn("attachment", response["Content-Disposition"])

    def test_csrf_required_on_instructor_and_enrollment_posts(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        self.assertEqual(client.post(reverse("enroll", args=[self.module.pk])).status_code, 403)
        client.force_login(self.teacher)
        self.assertEqual(client.post(reverse("module_create"), {"code": "NEW", "title": "New"}).status_code, 403)

    def test_credential_response_does_not_expose_password(self):
        self.client.force_login(self.teacher)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("quick_add_candidate"), data=json.dumps({
                "username": "P100", "password": "Strong-pass-331", "email": "p100@example.test"}),
                content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password", response.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)
        self.assertNotIn("Strong-pass-331", mail.outbox[0].body)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ExamMailTests(Base):
    def test_start_and_submit_send_exactly_once_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            attempt = start_attempt(self.exam, self.user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("started", mail.outbox[0].subject)
        with self.captureOnCommitCallbacks(execute=True):
            start_attempt(self.exam, self.user)
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            submit_attempt(attempt, actor=self.user)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("submitted", mail.outbox[1].subject)
        with self.captureOnCommitCallbacks(execute=True):
            submit_attempt(attempt, actor=self.user)
        self.assertEqual(len(mail.outbox), 2)


@override_settings(RESEND_API_KEY="test-token")
class ResendBackendTests(TestCase):
    @patch("exams.resend_backend.urlopen")
    def test_post_resend_payload(self, post):
        from django.core.mail import EmailMessage
        from .resend_backend import ResendBackend
        post.return_value.__enter__.return_value.read.return_value = b'{}'
        self.assertEqual(ResendBackend().send_messages([EmailMessage("Subject", "Hello", "verified@example.test", ["to@example.test"])]), 1)
        request = post.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(json.loads(request.data)["to"], ["to@example.test"])
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
