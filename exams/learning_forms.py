from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Lesson, Module


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ("code", "title", "description", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ("title", "content", "attachment", "position", "published")
        widgets = {"content": forms.Textarea(attrs={"rows": 9})}

    def clean_attachment(self):
        file = self.cleaned_data.get("attachment")
        limit = 4 if getattr(settings, "VERCEL", False) else 10
        if file and file.size > limit * 1024 * 1024:
            raise ValidationError(f"Attachments must be {limit} MB or smaller.")
        return file

    def clean(self):
        data = super().clean()
        if not data.get("content", "").strip() and not data.get("attachment") and not (self.instance.pk and self.instance.attachment):
            raise ValidationError("Add lesson text or an attachment.")
        return data
