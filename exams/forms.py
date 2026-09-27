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
