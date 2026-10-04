from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import JsonResponse

from apps.public.models import BlogPost, SiteContent, Testimonial, ClinicSettings, Service, TeamMember
from apps.staff.forms import HomepageForm, AboutForm, ClinicSettingsForm

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
    content = SiteContent.objects.first()
    if not content:
        content, _ = SiteContent.objects.get_or_create(pk=1)

    active_tab = request.GET.get("tab", "homepage")

    if request.method == "POST":
        post_active_tab = request.POST.get("active_tab", "homepage")

        if post_active_tab == "about":
            about_form = AboutForm(request.POST, request.FILES, instance=content)
            homepage_form = HomepageForm(instance=content)
            active_form = about_form
        else:
            homepage_form = HomepageForm(request.POST, request.FILES, instance=content)
            about_form = AboutForm(instance=content)
            active_form = homepage_form

        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        if active_form.is_valid():
            active_form.save()
            messages.success(request, "Saved just now. You're editing the latest version.")
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "redirect_url": f"{request.path}?tab={post_active_tab}&saved=1"
                })
            return redirect(f"{request.path}?tab={post_active_tab}&saved=1")
        else:
            messages.error(request, "Some changes could not be saved. Please inspect the marked fields below.")
            if is_ajax:
                return JsonResponse({
                    "success": False,
                    "errors": active_form.errors.get_json_data()
                }, status=400)
            active_tab = post_active_tab

    else:
        homepage_form = HomepageForm(instance=content)
        about_form = AboutForm(instance=content)

    return render(
        request,
        "staff/pages/website.html",
        {
            "active_page": "website",
            "active_tab": active_tab,
            "homepage_form": homepage_form,
            "about_form": about_form,
            "content_object": content,
            "testimonial_count": Testimonial.objects.count(),
            "published_testimonial_count": Testimonial.objects.filter(is_published=True).count(),
            "blog_post_count": BlogPost.objects.count(),
            "published_blog_post_count": BlogPost.objects.filter(is_published=True).count(),
            "service_count": Service.objects.count(),
            "published_service_count": Service.objects.filter(is_published=True).count(),
            "team_count": TeamMember.objects.count(),
            "published_team_count": TeamMember.objects.filter(is_published=True).count(),
        },
    )


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def blog(request):
    return redirect("dashboard:blog")


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
    settings, _ = ClinicSettings.objects.get_or_create(pk=1)
    
    if request.method == "POST":
        form = ClinicSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Clinic settings updated successfully.")
            return redirect("dashboard:settings")
    else:
        form = ClinicSettingsForm(instance=settings)
        
    return render(
        request,
        "staff/pages/settings.html",
        {
            "active_page": "settings",
            "form": form,
        },
    )

