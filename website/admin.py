from django.contrib import admin
from .models import Appointment
from django.utils.html import format_html

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    # table columns
    list_display = ("id", "date", "timeslot", "name", "phone", "email", "services_pretty", "created_at")
    list_display_links = ("id", "name")

    # right sidebar filters
    list_filter = ("date", "timeslot", "created_at")

    # top search bar
    search_fields = ("name", "phone", "email")

    # date drilldown nav
    date_hierarchy = "date"

    # pagination
    list_per_page = 25

    # read-only auto fields
    readonly_fields = ("created_at",)

    # how the edit form is grouped
    fieldsets = (
        ("Patient", {"fields": ("name", "phone", "email")}),
        ("Booking", {"fields": ("date", "timeslot", "services")}),
        ("Notes",   {"fields": ("notes",)}),
        ("Meta",    {"fields": ("created_at",)}),
    )

    def services_pretty(self, obj):
        """
        JSONField -> readable comma list
        """
        if not obj.services:
            return "-"
        if isinstance(obj.services, (list, tuple)):
            return ", ".join(obj.services)
        return str(obj.services)
    services_pretty.short_description = "Services"
