from django.contrib.auth.views import LoginView

def staff_only(user):
    return user.is_authenticated and user.is_staff

class RememberMeLoginView(LoginView):
    template_name = "staff/pages/login.html"

    def form_valid(self, form):
        resp = super().form_valid(form)
        remember = self.request.POST.get("remember") == "on"
        # 2 weeks if checked; session-only if not
        self.request.session.set_expiry(1209600 if remember else 0)
        return resp