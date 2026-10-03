from django import forms

MAX_TOTAL_UPLOAD = 25 * 1024 * 1024

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".png,.jpg,.jpeg,.webp"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(item, initial) for item in files]

class ImportForm(forms.Form):
    spreadsheet = forms.FileField(
        label="Question spreadsheet",
        help_text="Upload the simple Excel template (.xlsx) or a CSV using the same columns.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.csv"}),
    )
    images = MultipleFileField(
        required=False,
        label="Question pictures (optional)",
        help_text="Select all referenced PNG, JPEG, or WebP files at once. No ZIP is needed.",
    )

    def clean_spreadsheet(self):
        f = self.cleaned_data["spreadsheet"]
        if f.size > 12 * 1024 * 1024:
            raise forms.ValidationError("The spreadsheet exceeds 12 MB.")
        if not f.name.lower().endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Use an XLSX or CSV spreadsheet.")
        return f

    def clean_images(self):
        files = self.cleaned_data.get("images", [])
        seen = set()
        for f in files:
            name = f.name.rsplit("/", 1)[-1]
            if name.lower() in seen:
                raise forms.ValidationError(f"Two selected pictures have the same filename: {name}.")
            seen.add(name.lower())
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError(f"{name} exceeds 5 MB.")
            if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                raise forms.ValidationError(f"{name} is not a PNG, JPEG, or WebP image.")
        return files

    def clean(self):
        cleaned = super().clean()
        items = [cleaned.get("spreadsheet"), *cleaned.get("images", [])]
        if sum(getattr(f, "size", 0) for f in items if f) > MAX_TOTAL_UPLOAD:
            raise forms.ValidationError("The spreadsheet and pictures exceed the 25 MB upload limit.")
        return cleaned


class CreateExamForm(forms.Form):
    title = forms.CharField(
        label="Examination Title",
        max_length=180,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Air Law & ATC Procedures Assessment"}),
    )
    module_name = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.HiddenInput(),
    )
    duration_minutes = forms.IntegerField(
        label="Duration (Minutes)",
        initial=30,
        min_value=1,
        max_value=480,
    )
    pass_mark = forms.DecimalField(
        label="Pass Mark (%)",
        initial=75,
        min_value=0,
        max_value=100,
    )
    max_attempts = forms.IntegerField(
        label="Allowed Attempts",
        initial=1,
        min_value=1,
        max_value=10,
    )
    question_count = forms.IntegerField(
        label="Questions Per Attempt",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"placeholder": "All (or e.g. 25)"}),
    )
    shuffle_questions = forms.BooleanField(
        label="Randomize question order for each candidate attempt",
        initial=True,
        required=False,
    )
    shuffle_options = forms.BooleanField(
        label="Randomize answer options (A, B, C, D) for each question",
        initial=True,
        required=False,
    )
    show_answers_after = forms.BooleanField(
        label="Allow students to review answer solutions after submission",
        initial=False,
        required=False,
    )
    available_from = forms.DateTimeField(
        label="Opens At",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "id": "id_available_from"}),
    )
    available_until = forms.DateTimeField(
        label="Closes At",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "id": "id_available_until"}),
    )
    spreadsheet = forms.FileField(
        label="Question Spreadsheet (.xlsx or .csv)",
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx,.csv"}),
        required=True,
    )
    images = MultipleFileField(
        required=False,
        label="Question Diagrams / Pictures (Optional)",
    )
    candidates = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Assign to Students Immediately",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["candidates"].queryset = User.objects.filter(is_staff=False).order_by("username")

    def clean_spreadsheet(self):
        f = self.cleaned_data["spreadsheet"]
        if f.size > 12 * 1024 * 1024:
            raise forms.ValidationError("The spreadsheet exceeds 12 MB.")
        if not f.name.lower().endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Use an XLSX or CSV spreadsheet.")
        return f

    def clean_images(self):
        files = self.cleaned_data.get("images", [])
        seen = set()
        for f in files:
            name = f.name.rsplit("/", 1)[-1]
            if name.lower() in seen:
                raise forms.ValidationError(f"Two selected pictures have the same filename: {name}.")
            seen.add(name.lower())
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError(f"{name} exceeds 5 MB.")
            if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                raise forms.ValidationError(f"{name} is not a PNG, JPEG, or WebP image.")
        return files

    def clean(self):
        cleaned = super().clean()
        af = cleaned.get("available_from")
        au = cleaned.get("available_until")
        if af and au and af >= au:
            raise forms.ValidationError("Exam expiration time must be after the start time.")
        return cleaned

