from django import forms

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
