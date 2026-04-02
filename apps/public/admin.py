from django.contrib import admin
from .models import SiteContent

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("id", "hero_title", "updated_at")
    readonly_fields = ("created_at", "updated_at")