"""Regression checks for the Render-era source review."""
import io
import json
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .learning_forms import ModuleForm, LessonForm
from .models import Module, Lesson, Category, Question, Attempt, Response, Option, AuditEvent
from .services import start_attempt, save_response, submit_attempt
from .tests import Base


class BootstrapTests(TestCase):
    def test_no_credentials_never_creates_default_admin(self):
        with patch.dict(os.environ, {}, clear=True):
            call_command("ensure_admin", stdout=io.StringIO())
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_existing_administrator_is_unchanged_and_demo_data_is_not_purged(self):
        admin = get_user_model().objects.create_superuser("admin", "real@example.test", "Original-strong-489")
        module = Module.objects.create(code="DEMO", title="Retain these records")
        category = Category.objects.create(module=module, code="KEEP", title="Keep")
        Question.objects.create(code="DEMO-Q", module=module, category=category, stem="Keep")
        with patch.dict(os.environ, {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "Different-strong-782"}, clear=True):
            call_command("ensure_admin", stdout=io.StringIO())
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Original-strong-489"))
        self.assertEqual(admin.email, "real@example.test")
        self.assertTrue(Module.objects.filter(pk=module.pk).exists())

    def test_student_cannot_be_promoted_by_bootstrap(self):
        student = get_user_model().objects.create_user("admin", password="Original-strong-489")
        with patch.dict(os.environ, {"ADMIN_USERNAME": "admin", "ADMIN_PASSWORD": "Different-strong-782"}, clear=True):
            with self.assertRaises(CommandError):
                call_command("ensure_admin", stdout=io.StringIO())
        student.refresh_from_db()
        self.assertFalse(student.is_staff)

    def test_explicit_bootstrap_is_created_once(self):
        with patch.dict(os.environ, {"ADMIN_USERNAME": "academyadmin", "ADMIN_PASSWORD": "Random-strong-782",
                                   "ADMIN_EMAIL": "admin@example.test"}, clear=True):
            call_command("ensure_admin", stdout=io.StringIO())
            call_command("ensure_admin", stdout=io.StringIO())
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertTrue(get_user_model().objects.get().is_superuser)


class ExamSafetyTests(Base):
    def test_staff_preview_is_read_only_even_after_deadline(self):
        attempt = start_attempt(self.exam, self.user)
        Attempt.objects.filter(pk=attempt.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.client.force_login(self.staff)
        url = reverse("question", args=[attempt.pk, 1])
        response = self.client.get(url)
        self.assertContains(response, "Read-only instructor preview")
        self.assertNotContains(response, "js/exam.js")
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.IN_PROGRESS)
        self.assertIsNone(attempt.attempt_questions.get(position=1).first_viewed_at)
        self.assertEqual(self.client.post(reverse("finish", args=[attempt.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("answer", args=[attempt.pk, 1]), {"selected": "A"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("flag_question", args=[attempt.pk, 1])).status_code, 404)

    def test_dashboard_never_publishes_drafts_or_moves_similar_modules(self):
        Question.objects.filter(module=self.module).update(status=Question.DRAFT)
        self.client.force_login(self.user)
        self.client.get(reverse("dashboard"))
        self.assertEqual(Question.objects.filter(status=Question.PUBLISHED).count(), 0)
        with self.assertRaises(ValidationError):
            start_attempt(self.exam, self.user)

    def test_small_stratified_target_never_overdraws_sparse_categories(self):
        from .services import sample_stratified_questions
        import random
        from types import SimpleNamespace
        pool = [SimpleNamespace(category_id=i, code=str(i)) for i in range(6)]
        for count in range(7):
            chosen = sample_stratified_questions(pool, count, random.Random(100 + count))
            self.assertEqual(len(chosen), count)
            self.assertEqual(len({q.code for q in chosen}), count)

    def test_start_requires_full_configured_question_pool(self):
        self.exam.question_count = 20
        self.exam.save()
        with self.assertRaises(ValidationError):
            start_attempt(self.exam, self.user)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.question_count, 20)
        self.assertEqual(Attempt.objects.count(), 0)

    def test_response_must_belong_to_locked_attempt(self):
        one = start_attempt(self.exam, self.user)
        submit_attempt(one)
        two = start_attempt(self.exam, self.user)
        with self.assertRaises(ValidationError):
            save_response(two, one.attempt_questions.first(), ["A"], actor=self.user)
        self.assertEqual(Response.objects.filter(attempt_question__attempt=two).count(), 0)

    def test_deadline_applies_even_without_expired_flag(self):
        attempt = start_attempt(self.exam, self.user)
        Attempt.objects.filter(pk=attempt.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        submit_attempt(attempt, actor=self.user)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.EXPIRED)

    def test_resume_expiry_survives_attempt_limit_error(self):
        self.exam.max_attempts = 1
        self.exam.save()
        attempt = start_attempt(self.exam, self.user)
        Attempt.objects.filter(pk=attempt.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            start_attempt(self.exam, self.user)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.EXPIRED)

    def test_closed_attempt_cannot_be_flagged(self):
        attempt = start_attempt(self.exam, self.user)
        submit_attempt(attempt, actor=self.user)
        self.client.force_login(self.user)
        response = self.client.post(reverse("flag_question", args=[attempt.pk, 1]))
        self.assertEqual(response.status_code, 409)
        self.assertFalse(attempt.attempt_questions.get(position=1).flagged)

    def test_staff_cannot_force_expiry_in_service(self):
        attempt = start_attempt(self.exam, self.user)
        with self.assertRaises(ValidationError):
            submit_attempt(attempt, expired=True, actor=self.staff)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.IN_PROGRESS)

    def test_exam_with_attempts_cannot_be_deleted(self):
        attempt = start_attempt(self.exam, self.user)
        self.client.force_login(self.staff)
        self.client.post(reverse("delete_exam", args=[self.exam.pk]))
        self.assertTrue(Attempt.objects.filter(pk=attempt.pk).exists())
        self.assertTrue(type(self.exam).objects.filter(pk=self.exam.pk).exists())

    def test_multi_module_exam_import_rejects_before_writing(self):
        from .importers import import_simple_questions
        raw = b"Module,Question,Option A,Option B,Correct Answer\nOne,First?,Yes,No,A\nTwo,Second?,Yes,No,A\n"
        result = import_simple_questions(SimpleUploadedFile("mixed.csv", raw), [], self.staff, require_single_module=True)
        self.assertFalse(result["ok"])
        self.assertFalse(Module.objects.filter(code="ONE").exists())

    def test_exam_create_keeps_categories_aligned_and_unrelated_drafts(self):
        draft = Question.objects.create(code="UNREVIEWED", module=self.module, category=self.cat, stem="Draft")
        self.client.force_login(self.staff)
        raw = b"Module,Category,Question,Option A,Option B,Correct Answer\nAir Law,RULES,New imported?,Yes,No,A\n"
        response = self.client.post(reverse("create_exam"), {"title": "Review exam", "module_name": "Air Law",
                   "duration_minutes": 30, "pass_mark": 75, "max_attempts": 1,
                   "spreadsheet": SimpleUploadedFile("single.csv", raw), "question_count": 1})
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, Question.DRAFT)
        q = Question.objects.get(stem="New imported?")
        self.assertEqual(q.module_id, q.category.module_id)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", PUBLIC_BASE_URL="https://academy.example.test")
class AccountSafetyTests(Base):
    def test_malformed_or_duplicate_candidate_requests_are_400(self):
        self.client.force_login(self.staff)
        url = reverse("quick_add_candidate")
        payloads = [[], {"username": 42}, {"username": "OK", "email": "invalid"},
                    {"username": "NEW", "email": self.user.email}, {"username": "x" * 151, "email": "new@example.test"}]
        for data in payloads:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(url, json.dumps(data), content_type="application/json").status_code, 400)

    def test_signup_rejects_case_insensitive_duplicate_username(self):
        from .learning_forms import SignUpForm
        form = SignUpForm({"username": "c001", "email": "unique@example.test",
                           "password1": "Strong-pass-744", "password2": "Strong-pass-744"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_ambiguous_legacy_username_login_fails_closed(self):
        User = get_user_model()
        User.objects.create_user("C001".lower(), password="Strong-pass-473")
        self.assertFalse(self.client.login(username="C001", password="Strong-pass-473"))

    def test_email_link_is_absolute_and_uses_public_origin(self):
        with self.captureOnCommitCallbacks(execute=True):
            start_attempt(self.exam, self.user)
        self.assertIn("https://academy.example.test/dashboard/", mail.outbox[0].body)
        self.assertIn("https://academy.example.test/dashboard/", mail.outbox[0].alternatives[0].content)

    def test_instructor_with_user_permissions_cannot_edit_or_reset_admin(self):
        User = get_user_model()
        teacher = User.objects.create_user("teacher", password="Teacher-strong-349", is_staff=True)
        teacher.user_permissions.set(Permission.objects.filter(content_type__app_label="auth", codename__in=["view_user", "change_user", "delete_user"]))
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(reverse("admin:auth_user_change", args=[self.staff.pk])).status_code, 302)
        from .admin import CustomUserAdmin
        from django.contrib import admin
        from django.test import RequestFactory
        request = RequestFactory().get("/admin/")
        request.user = teacher
        model_admin = CustomUserAdmin(User, admin.site)
        self.assertFalse(model_admin.has_change_permission(request, self.staff))
        self.assertFalse(model_admin.has_delete_permission(request, self.staff))
        self.assertFalse(model_admin.get_queryset(request).filter(pk=self.staff.pk).exists())


class FormAndHealthTests(TestCase):
    def test_reserved_and_unroutable_module_codes_rejected(self):
        for code in ["NEW", "flight/one", "flight two", "?module"]:
            form = ModuleForm({"code": code, "title": "Module"})
            self.assertFalse(form.is_valid(), code)
        self.assertTrue(ModuleForm({"code": "FLIGHT_1", "title": "Module"}).is_valid())

    def test_disabled_existing_module_code_is_not_renamed(self):
        module = Module.objects.create(code="legacy_code", title="Legacy")
        form = ModuleForm({"title": "Updated", "active": "on"}, instance=module)
        form.fields["code"].disabled = True
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.pk, "legacy_code")
        self.assertEqual(Module.objects.count(), 1)

    def test_removing_only_attachment_requires_lesson_content(self):
        module = Module.objects.create(code="MOD", title="Module")
        lesson = Lesson.objects.create(module=module, title="Lesson", attachment="existing.pdf")
        form = LessonForm({"title": "Lesson", "content": "", "attachment-clear": "on", "position": 1}, instance=lesson)
        self.assertFalse(form.is_valid())

    def test_health_endpoint_checks_database(self):
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})
        from django.db import OperationalError
        with patch("config.health.connection.cursor", side_effect=OperationalError("private database details")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.content.decode())

    def test_csv_cells_cannot_execute_formulas(self):
        from .admin import safe_csv_cell
        for value in ["=1+1", "+SUM(1)", "-2+3", "@SUM(A1)", "\tformula", "  =HYPERLINK(1)"]:
            self.assertTrue(safe_csv_cell(value).startswith("'"))
        self.assertEqual(safe_csv_cell("ordinary name"), "ordinary name")
        self.assertEqual(safe_csv_cell(42), 42)
