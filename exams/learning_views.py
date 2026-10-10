"""Accessible student-facing course pages and instructor authoring tools."""
from pathlib import PurePosixPath
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .emailing import welcome
from .learning_forms import LessonForm, ModuleForm, SignUpForm
from .models import Enrollment, Lesson, Module


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not getattr(settings, "PUBLIC_SIGNUP", True):
        raise Http404
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        welcome(user, request.build_absolute_uri("/").rstrip("/"))
        login(request, user, backend="exams.auth.UsernameOrEmailBackend")
        messages.success(request, "Your student account is ready. Browse modules to get started.")
        return redirect("module_catalog")
    return render(request, "exams/signup.html", {"form": form})


@login_required
def module_catalog(request):
    modules = Module.objects.filter(active=True)
    if request.user.is_staff:
        from django.db.models import Q
        modules = Module.objects.all() if request.user.is_superuser else Module.objects.filter(Q(active=True) | Q(instructor=request.user))
    modules = modules.select_related("instructor").order_by("title")
    enrolled = set(Enrollment.objects.filter(student=request.user).values_list("module_id", flat=True))
    return render(request, "exams/modules.html", {"modules": modules, "enrolled": enrolled})


@login_required
def module_detail(request, code):
    module = get_object_or_404(Module, pk=code)
    enrolled = Enrollment.objects.filter(module=module, student=request.user).exists()
    if not module.active and not can_edit(request.user, module):
        raise Http404
    lessons = module.lessons.all() if can_edit(request.user, module) else module.lessons.filter(published=True) if enrolled else module.lessons.none()
    return render(request, "exams/module_detail.html", {"module": module, "enrolled": enrolled,
                                                         "lessons": lessons, "can_edit": can_edit(request.user, module)})


def can_edit(user, module):
    return user.is_active and user.is_staff and (user.is_superuser or module.instructor_id == user.pk)


@login_required
@require_POST
def enroll(request, code):
    module = get_object_or_404(Module, pk=code, active=True)
    if request.user.is_staff:
        messages.error(request, "Instructor accounts cannot enroll as students.")
    else:
        Enrollment.objects.get_or_create(module=module, student=request.user)
        messages.success(request, "You are enrolled. Your lessons are now available.")
    return redirect("module_detail", code=module.pk)


@user_passes_test(lambda u: u.is_active and u.is_staff)
def module_create(request):
    form = ModuleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        module = form.save(commit=False)
        module.instructor = request.user
        module.save()
        messages.success(request, "Module created. Add lessons before sharing it with students.")
        return redirect("module_detail", code=module.pk)
    return render(request, "exams/edit_content.html", {"form": form, "heading": "Create module"})


@user_passes_test(lambda u: u.is_active and u.is_staff)
def module_edit(request, code):
    module = get_object_or_404(Module, pk=code)
    if not can_edit(request.user, module):
        raise Http404
    form = ModuleForm(request.POST or None, instance=module)
    # Changing a primary key would orphan related content in Django; keep the code stable.
    form.fields["code"].disabled = True
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Module updated.")
        return redirect("module_detail", code=module.pk)
    return render(request, "exams/edit_content.html", {"form": form, "heading": "Edit module"})


@user_passes_test(lambda u: u.is_active and u.is_staff)
def lesson_edit(request, code, lesson_id=None):
    module = get_object_or_404(Module, pk=code)
    if not can_edit(request.user, module):
        raise Http404
    lesson = get_object_or_404(Lesson, pk=lesson_id, module=module) if lesson_id else None
    form = LessonForm(request.POST or None, request.FILES or None, instance=lesson)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.module = module
        obj.save()
        messages.success(request, "Lesson saved.")
        return redirect("module_detail", code=code)
    return render(request, "exams/edit_content.html", {"form": form, "heading": "Edit lesson" if lesson else "Add lesson",
                                                         "upload": True})


@login_required
def lesson_detail(request, code, lesson_id):
    module = get_object_or_404(Module, pk=code)
    lesson = get_object_or_404(Lesson, pk=lesson_id, module=module)
    if not can_edit(request.user, module) and not (module.active and lesson.published and
            Enrollment.objects.filter(student=request.user, module=module).exists()):
        raise Http404
    return render(request, "exams/lesson.html", {"lesson": lesson, "module": module, "can_edit": can_edit(request.user, module)})


@login_required
def lesson_attachment(request, code, lesson_id):
    module = get_object_or_404(Module, pk=code)
    lesson = get_object_or_404(Lesson, pk=lesson_id, module=module)
    if not lesson.attachment or not (can_edit(request.user, module) or (module.active and lesson.published and
            Enrollment.objects.filter(student=request.user, module=module).exists())):
        raise Http404
    name = lesson.attachment.name
    if not default_storage.exists(name):
        raise Http404
    response = FileResponse(default_storage.open(name, "rb"), as_attachment=True,
                            filename=PurePosixPath(name).name)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
