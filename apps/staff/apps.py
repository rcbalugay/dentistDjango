from django.apps import AppConfig
from django.db.models.signals import post_migrate


class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.staff"

    def ready(self):
        from .signals import on_post_migrate
        post_migrate.connect(on_post_migrate, sender=self)

        # Restrict Django Admin to Administrators and superusers only
        from django.contrib import admin
        from django.core.exceptions import PermissionDenied
        from .permissions import is_administrator

        original_admin_view = admin.site.admin_view

        def custom_admin_view(view, cacheable=False):
            view_func = original_admin_view(view, cacheable=cacheable)
            def wrapper(request, *args, **kwargs):
                if request.user.is_authenticated and not is_administrator(request.user):
                    raise PermissionDenied("Administrator access required for Django Admin.")
                return view_func(request, *args, **kwargs)
            return wrapper

        admin.site.admin_view = custom_admin_view
        admin.site.has_permission = lambda request: is_administrator(request.user)
