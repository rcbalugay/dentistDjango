from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from apps.public.models import SiteContent
from apps.staff.forms import SiteContentForm

from .auth import staff_only

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def inquiries(request):
    return render(
        request,
        "staff/pages/inquiries.html",
        {
            "active_page": "inquiries",
        },
    )


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def message(request):
    return redirect("dashboard:inquiries")


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def website(request):
    content, _ = SiteContent.objects.get_or_create(pk=1)

    if request.method == "POST":
        form = SiteContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            form.save()
            return redirect(f"{request.path}?saved=1")
    else:
        form = SiteContentForm(instance=content)

    return render(
        request,
        "staff/pages/website.html",
        {
            "active_page": "website",
            "form": form,
            "content_object": content,
        },
    )


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def blog(request):
    return redirect("dashboard:website")


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def profile(request):
    return render(
        request,
        "staff/pages/profile.html",
        {
            "active_page": "profile",
        },
    )


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def settings_page(request):
    return render(
        request,
        "staff/pages/settings.html",
        {
            "active_page": "settings",
        },
    )
