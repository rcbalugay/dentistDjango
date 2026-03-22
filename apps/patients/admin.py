from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "patient_code", "name", "phone", "email", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("patient_code", "name", "phone", "email")
    list_filter = ("created_at",)
    ordering = ("name",)
    readonly_fields = ("created_at", "patient_code")
