from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .models import Module, Category, Question, Option, Exam, Assignment, Attempt, AuditEvent
from .services import validate_question

# Unregister Group to keep Authentication simple
admin.site.unregister(Group)

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
    list_display = ("title", "duration_minutes", "question_count", "pass_mark", "max_attempts", "status")
    list_filter = ("status",)
    search_fields = ("code", "title")
    inlines = [AssignmentInline]
    fieldsets = (
        (None, {"fields": ("code", "title", "module", "status")}),
        ("Timing & Rules", {"fields": ("duration_minutes", "pass_mark", "question_count", "max_attempts", "instructions")}),
        ("Shuffling & Display", {"fields": ("shuffle_questions", "shuffle_options", "show_answers_after")}),
        ("Schedule (Optional)", {"fields": ("available_from", "available_until")}),
    )

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    verbose_name = "Candidate Submission"
    verbose_name_plural = "Candidate Submissions"
    list_display = ("exam", "candidate", "attempt_number", "status", "percentage", "passed", "started_at", "submitted_at")
    list_filter = ("exam", "status", "passed")
    search_fields = ("candidate__username", "candidate__first_name", "candidate__last_name")
    readonly_fields = [f.name for f in Attempt._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

admin.site.site_header = "Africa Drone Kings"
admin.site.site_title = "Africa Drone Kings"
admin.site.index_title = "Academy Management"
