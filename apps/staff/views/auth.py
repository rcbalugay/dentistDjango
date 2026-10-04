from django.contrib.auth.views import LoginView
from apps.staff.permissions import is_active_staff


def staff_only(user):
    """
    Legacy helper maintained for backward compatibility.
    Enforces active staff with a recognized role or superuser.
    """
    return is_active_staff(user)


class RememberMeLoginView(LoginView):
    template_name = "staff/pages/login.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        remember = self.request.POST.get("remember") == "on"
        self.request.session.set_expiry(1209600 if remember else 0)
        return resp
