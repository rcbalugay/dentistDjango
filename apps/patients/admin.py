from django.contrib import admin

from .models import Patient, AuditLog


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "patient_code", "name", "phone", "email", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("patient_code", "name", "phone", "email")
    list_filter = ("created_at",)
    ordering = ("name",)
    readonly_fields = ("created_at", "patient_code")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model_name", "object_id", "description", "ip_address")
    list_filter = ("action", "model_name", "timestamp")
    search_fields = ("user__username", "description", "model_name")
    ordering = ("-timestamp",)
    readonly_fields = ("timestamp", "user", "action", "model_name", "object_id", "description", "ip_address")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

