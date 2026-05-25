from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import PatientDocument


class PatientDocumentForm(forms.ModelForm):
    class Meta:
        model = PatientDocument
        fields = ("title", "document_type", "file")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Document title",
                    "class": "form-control form-control-sm",
                }
            ),
            "document_type": forms.Select(
                attrs={"class": "form-control form-control-sm"}
            ),
            "file": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
        }

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # 1. Max file size of 10MB (10 * 1024 * 1024 bytes)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("File size must be under 10MB.")

            # 2. Allowed file extensions check (JPG, PNG, PDF, DOCX)
            suffix = Path(file.name).suffix.lower()
            allowed_suffixes = {".jpg", ".jpeg", ".png", ".pdf", ".docx"}
            if suffix not in allowed_suffixes:
                raise ValidationError("Invalid file format. Only JPG, PNG, PDF, and DOCX are allowed.")
        return file
