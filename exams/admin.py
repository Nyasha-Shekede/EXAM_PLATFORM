from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils.html import format_html
from .models import Module, Category, Question, Option, Exam, Assignment, Attempt, AuditEvent
from .services import validate_question

# Unregister default User and Group to eliminate bloated permissions and complex forms
admin.site.unregister(Group)
admin.site.unregister(User)

class UserRoleFilter(admin.SimpleListFilter):
    title = "Role"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return [
            ("instructor", "Instructor"),
            ("student", "Student"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "instructor":
            return queryset.filter(is_staff=True)
        if self.value() == "student":
            return queryset.filter(is_staff=False)
        return queryset

class UserStatusFilter(admin.SimpleListFilter):
    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [
            ("active", "Active"),
            ("inactive", "Inactive"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_active=True)
        if self.value() == "inactive":
            return queryset.filter(is_active=False)
        return queryset

class CustomUserCreationForm(forms.ModelForm):
    first_name = forms.CharField(label="First Name", max_length=150, required=False)
    last_name = forms.CharField(label="Last Name", max_length=150, required=False)
    email = forms.EmailField(label="Email Address", required=True, help_text="Required. An automated invite link will be emailed to set their password.")
    role = forms.ChoiceField(
        label="Account Role",
        choices=[("student", "Student (Candidate) - Sets own password via email invite"), ("instructor", "Instructor (Staff) - Platform manager")],
        initial="student",
        widget=forms.RadioSelect,
        help_text="Candidates choose their own private password via invite email. Instructors can have an initial password set by administrators."
    )
    password1 = forms.CharField(
        label="Password (Instructors only)",
        widget=forms.PasswordInput,
        required=False,
        help_text="Optional. Only applicable when creating an Instructor account. Leave blank for Students."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role", "student")
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if role == "instructor" and p1:
            if p1 != p2:
                raise ValidationError("Instructor passwords do not match.")
            if len(p1) < 8:
                raise ValidationError("Instructor password must be at least 8 characters long.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.email = self.cleaned_data.get("email", "")
        role = self.cleaned_data.get("role", "student")
        p1 = self.cleaned_data.get("password1")
        if role == "instructor":
            user.is_staff = True
            if p1:
                user.set_password(p1)
            else:
                user.set_unusable_password()
        else:
            user.is_staff = False
            user.is_superuser = False
            # Candidates NEVER have passwords set by instructors
            user.set_unusable_password()
        if commit:
            user.save()
        return user

class CleanPasswordWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        return format_html(
            '<div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 6px;">'
            '<span style="font-family: monospace; font-size: 16px; letter-spacing: 0.25em; color: #475569; background: #f1f5f9; padding: 6px 12px; border-radius: 6px; border: 1px solid #cbd5e1;">••••••••••••</span>'
            '<a href="../password/" class="button" style="background: #1483c6; color: #ffffff; padding: 7px 14px; border-radius: 6px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; text-decoration: none; display: inline-block;">Change Password</a>'
            '</div>'
            '<span class="help" style="color: #64748b; font-size: 12px; display: block;">Raw passwords are encrypted for security. Candidates set and manage their own passwords via email invite.</span>'
        )

class CustomUserChangeForm(UserChangeForm):
    password = forms.CharField(label="Password", widget=CleanPasswordWidget, required=False)
    role = forms.ChoiceField(
        label="Account Role",
        choices=[("student", "Student (Candidate)"), ("instructor", "Instructor (Staff)")],
        widget=forms.RadioSelect,
        help_text="Select whether this user is an examination student or an academy instructor."
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("username", "password", "first_name", "last_name", "email", "role", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["role"].initial = "instructor" if (self.instance.is_staff or self.instance.is_superuser) else "student"

    def clean_password(self):
        return self.initial.get("password")

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get("role", "student")
        if role == "instructor":
            user.is_staff = True
        else:
            user.is_staff = False
            user.is_superuser = False
        if commit:
            user.save()
        return user

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    actions = ["delete_selected", "send_password_reset_email"]

    @admin.action(description="Send Password Setup / Reset email to selected users")
    def send_password_reset_email(self, request, queryset):
        from .emailing import welcome
        base_url = request.build_absolute_uri("/").rstrip("/")
        sent = 0
        for u in queryset:
            if u.email:
                welcome(u, base_url, password_setup=True)
                sent += 1
        from django.contrib import messages
        messages.success(request, f"Password setup/reset email dispatched to {sent} user(s).")

    def user_change_password(self, request, id, form_url=""):
        user = self.get_object(request, id)
        # Block regular staff from setting candidate passwords directly
        if user and not user.is_staff and not request.user.is_superuser:
            from django.contrib import messages
            messages.error(request, "Security Policy: Instructors cannot manually type candidate passwords. Use the 'Send Password Setup / Reset email' action instead.")
            return redirect("..")
        return super().user_change_password(request, id, form_url)

    def save_model(self, request, obj, form, change):
        # Prevent non-superusers from creating or promoting instructors
        if not request.user.is_superuser:
            role = form.cleaned_data.get("role", "student")
            if role == "instructor" or obj.is_staff or obj.is_superuser:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Only Academy Administrators (Superusers) can create or promote Instructor accounts.")

        super().save_model(request, obj, form, change)
        if not change and obj.email:
            from .emailing import welcome
            welcome(obj, request.build_absolute_uri("/").rstrip("/"), password_setup=True)
        if change and "password" in getattr(form, "changed_data", []):
            from .services import audit, client_ip
            audit("STAFF_CHANGED_USER_PASSWORD", obj, request.user, {
                "target_username": obj.username,
                "target_email": obj.email,
            }, client_ip(request))



    list_display = ("username", "full_name_display", "email", "role_badge", "active_badge", "date_joined")
    list_filter = (UserRoleFilter, UserStatusFilter)
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    filter_horizontal = ()

    if hasattr(admin, "ShowFacets"):
        show_facets = admin.ShowFacets.NEVER

    fieldsets = (
        ("Account Credentials", {"fields": ("username", "password")}),
        ("Personal Information", {"fields": ("first_name", "last_name", "email")}),
        ("Role & Access", {"fields": ("role", "is_active")}),
    )

    add_fieldsets = (
        ("Create User", {
            "classes": ("wide",),
            "fields": ("username", "first_name", "last_name", "email", "role", "password1", "password2"),
        }),
    )

    @admin.display(description="Full Name")
    def full_name_display(self, obj):
        name = obj.get_full_name()
        return name if name else "—"

    @admin.display(description="Role")
    def role_badge(self, obj):
        if obj.is_staff or obj.is_superuser:
            return format_html('<span style="font-size: 11px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #1483c6; background: #e8f4fc; padding: 3px 8px; border-radius: 6px; border: 1px solid #bfdbfe;">Instructor</span>')
        return format_html('<span style="font-size: 11px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: #475569; background: #f1f5f9; padding: 3px 8px; border-radius: 6px; border: 1px solid #cbd5e1;">Student</span>')

    @admin.display(description="Active", boolean=True)
    def active_badge(self, obj):
        return obj.is_active

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    min_num = 2

class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 1
    autocomplete_fields = ["candidate"]
    verbose_name = "Candidate Assignment"
    verbose_name_plural = "Assigned Candidates"

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("exam", "candidate", "active", "assigned_at")
    list_filter = ("exam", "active")
    search_fields = ("exam__title", "candidate__username", "candidate__first_name", "candidate__last_name")
    autocomplete_fields = ["exam", "candidate"]

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if "exam" in request.GET:
            initial["exam"] = request.GET["exam"]
        return initial

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "module", "question_type", "difficulty", "status", "version", "updated_at")
    list_filter = ("module", "question_type", "difficulty", "status")
    search_fields = ("code", "stem")
    inlines = [OptionInline]
    readonly_fields = ("image_sha256", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("code", "module", "question_type", "stem", "explanation")}),
        ("Assessment", {"fields": ("marks", "difficulty", "status", "version")}),
        ("Diagram / Picture", {"fields": ("image", "image_alt_text", "image_sha256")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_at")}),
    )
    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        if not obj.category_id:
            cat, _ = Category.objects.get_or_create(module=obj.module, code="GENERAL", defaults={"title": "General"})
            obj.category = cat
        super().save_model(request, obj, form, change)

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "duration_minutes", "question_count", "pass_mark", "max_attempts", "status")
    list_filter = ("module", "status")
    search_fields = ("code", "title")
    inlines = [AssignmentInline]
    fieldsets = (
        (None, {"fields": ("code", "title", "module", "status")}),
        ("Timing & Rules", {"fields": ("duration_minutes", "pass_mark", "question_count", "max_attempts", "instructions")}),
        ("Shuffling & Display", {"fields": ("shuffle_questions", "shuffle_options", "show_answers_after")}),
        ("Schedule (Optional)", {"fields": ("available_from", "available_until")}),
    )

    def response_change(self, request, obj):
        super().response_change(request, obj)
        return redirect("dashboard")

    def response_add(self, request, obj, post_url_continue=None):
        super().response_add(request, obj, post_url_continue)
        return redirect("dashboard")

    def response_delete(self, request, obj_display, obj_id):
        super().response_delete(request, obj_display, obj_id)
        return redirect("dashboard")

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    verbose_name = "Candidate Submission"
    verbose_name_plural = "Candidate Submissions"
    list_display = ("exam", "candidate", "attempt_number", "status", "percentage", "passed", "started_at", "submitted_at")
    list_filter = ("exam", "status", "passed")
    search_fields = ("candidate__username", "candidate__first_name", "candidate__last_name")
    readonly_fields = [f.name for f in Attempt._meta.fields]
    actions = ["export_as_csv"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description="Export selected submissions to CSV")
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="candidate_submissions.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Exam", "Candidate_Username", "Candidate_Name", "Attempt_No", "Status", "Score", "Max_Score", "Percentage", "Passed", "Started_At", "Submitted_At", "Verification_Code"])
        for a in queryset.select_related("exam", "candidate"):
            writer.writerow([
                str(a.id),
                a.exam.title,
                a.candidate.username,
                a.candidate.get_full_name() or a.candidate.username,
                a.attempt_number,
                a.status,
                a.score if a.score is not None else "",
                a.max_score if a.max_score is not None else "",
                a.percentage if a.percentage is not None else "",
                "PASS" if a.passed else ("FAIL" if a.passed is False else ""),
                a.started_at.isoformat() if a.started_at else "",
                a.submitted_at.isoformat() if a.submitted_at else "",
                a.verification_code,
            ])
        return response

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    verbose_name = "Audit Log"
    verbose_name_plural = "Audit Logs"
    list_display = ("at", "action", "actor", "object_type", "object_id", "ip_address")
    list_filter = ("action", "object_type")
    search_fields = ("action", "object_id", "actor__username", "ip_address")
    readonly_fields = [f.name for f in AuditEvent._meta.fields]
    actions = ["export_as_csv"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Export selected audit events to CSV")
    def export_as_csv(self, request, queryset):
        import csv, json
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log_export.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Timestamp_UTC", "Actor", "Action", "Object_Type", "Object_ID", "IP_Address", "Details", "Event_Hash", "Previous_Hash"])
        for e in queryset.select_related("actor"):
            writer.writerow([
                e.id,
                e.at.isoformat() if e.at else "",
                e.actor.username if e.actor else "System",
                e.action,
                e.object_type,
                e.object_id,
                e.ip_address or "",
                json.dumps(e.details or {}),
                e.event_hash,
                e.previous_hash,
            ])
        return response


admin.site.site_header = "Africa Drone Kings"
admin.site.site_title = "Africa Drone Kings"
admin.site.index_title = "Academy Management"
