from django.contrib import admin

from .models import BlogPost, SiteContent, Testimonial

@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("id", "hero_title", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "visit_label", "sort_order", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("patient_name", "visit_label", "quote")
    ordering = ("sort_order", "id")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author_name", "published_at", "is_published", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "excerpt", "body", "author_name")
    prepopulated_fields = {"slug": ("title",)}
