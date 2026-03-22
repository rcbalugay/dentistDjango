from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "timeslot", "name", "phone", "email", "services_pretty", "created_at")
    list_display_links = ("id", "name")
    list_filter = ("date", "timeslot", "created_at")
    search_fields = ("name", "phone", "email")
    date_hierarchy = "date"
    list_per_page = 25
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Patient", {"fields": ("name", "phone", "email")}),
        ("Booking", {"fields": ("date", "timeslot", "services")}),
        ("Notes", {"fields": ("notes",)}),
        ("Meta", {"fields": ("created_at",)}),
    )

    def services_pretty(self, obj):
        if not obj.services:
            return "-"
        if isinstance(obj.services, (list, tuple)):
            return ", ".join(obj.services)
        return str(obj.services)

    services_pretty.short_description = "Services"
