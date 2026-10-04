from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.public.models import BlogPost, Testimonial, Service, TeamMember
from apps.staff.forms import BlogPostForm, TestimonialForm, ServiceForm, TeamMemberForm
from apps.staff.permissions import admin_required

from .auth import staff_only


def _render_content_form(request, template_name, form, title, subtitle):
    return render(
        request,
        template_name,
        {
            "active_page": "website",
            "form": form,
            "page_title": title,
            "page_subtitle": subtitle,
        },
    )


def _parse_selected_ids(raw_ids):
    selected_ids = []
    for value in (raw_ids or "").split(","):
        value = value.strip()
        if value.isdigit():
            selected_ids.append(int(value))
    return selected_ids


@admin_required
def testimonials(request):
    items = Testimonial.objects.all()
    return render(
        request,
        "staff/pages/testimonials.html",
        {
            "active_page": "website",
            "testimonials": items,
            "testimonial_count": items.count(),
            "published_testimonial_count": items.filter(is_published=True).count(),
        },
    )


@admin_required
def testimonial_create(request):
    if request.method == "POST":
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Testimonial created.")
            return redirect("dashboard:testimonials")
    else:
        form = TestimonialForm()

    return _render_content_form(
        request,
        "staff/pages/testimonial_form.html",
        form,
        "Add Testimonial",
        "Create a new testimonial for the homepage carousel.",
    )


@admin_required
def testimonial_edit(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)

    if request.method == "POST":
        form = TestimonialForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, "Testimonial updated.")
            return redirect("dashboard:testimonials")
    else:
        form = TestimonialForm(instance=testimonial)

    return _render_content_form(
        request,
        "staff/pages/testimonial_form.html",
        form,
        "Edit Testimonial",
        "Update quote details, ordering, and publish state.",
    )


@admin_required
def testimonial_delete(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    if request.method == "POST":
        testimonial.delete()
        messages.success(request, "Testimonial deleted.")
    return redirect("dashboard:testimonials")


@admin_required
def testimonial_bulk_action(request):
    if request.method == "POST":
        selected_ids = _parse_selected_ids(request.POST.get("selected_ids"))
        action = request.POST.get("bulk_action")

        if not selected_ids:
            messages.warning(request, "Select at least one testimonial first.")
            return redirect("dashboard:testimonials")

        queryset = Testimonial.objects.filter(pk__in=selected_ids)
        count = queryset.count()

        if action == "publish":
            queryset.update(is_published=True, updated_at=timezone.now())
            messages.success(request, f"Published {count} testimonial(s).")
        elif action == "hide":
            queryset.update(is_published=False, updated_at=timezone.now())
            messages.success(request, f"Hidden {count} testimonial(s).")
        elif action == "delete":
            queryset.delete()
            messages.success(request, f"Deleted {count} testimonial(s).")
        else:
            messages.error(request, "Choose a valid bulk action.")

    return redirect("dashboard:testimonials")


@admin_required
def testimonial_toggle_publish(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    if request.method == "POST":
        testimonial.is_published = not testimonial.is_published
        testimonial.save(update_fields=["is_published", "updated_at"])
        messages.success(
            request,
            "Testimonial published." if testimonial.is_published else "Testimonial hidden.",
        )
    return redirect("dashboard:testimonials")


@admin_required
def blog_posts(request):
    items = BlogPost.objects.all()
    return render(
        request,
        "staff/pages/blog_posts.html",
        {
            "active_page": "website",
            "blog_posts": items,
            "blog_post_count": items.count(),
            "published_blog_post_count": items.filter(is_published=True).count(),
        },
    )


@admin_required
def blog_post_create(request):
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog post created.")
            return redirect("dashboard:blog")
    else:
        form = BlogPostForm()

    return _render_content_form(
        request,
        "staff/pages/blog_post_form.html",
        form,
        "Add Blog Post",
        "Create a publishable article for the blog page and homepage preview cards.",
    )


@admin_required
def blog_post_edit(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)

    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog post updated.")
            return redirect("dashboard:blog")
    else:
        form = BlogPostForm(instance=post)

    return _render_content_form(
        request,
        "staff/pages/blog_post_form.html",
        form,
        "Edit Blog Post",
        "Update article copy, publish date, and cover image.",
    )


@admin_required
def blog_post_delete(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Blog post deleted.")
    return redirect("dashboard:blog")


@admin_required
def blog_post_bulk_action(request):
    if request.method == "POST":
        selected_ids = _parse_selected_ids(request.POST.get("selected_ids"))
        action = request.POST.get("bulk_action")

        if not selected_ids:
            messages.warning(request, "Select at least one blog post first.")
            return redirect("dashboard:blog")

        queryset = BlogPost.objects.filter(pk__in=selected_ids)
        count = queryset.count()

        if action == "publish":
            queryset.update(is_published=True, updated_at=timezone.now())
            messages.success(request, f"Published {count} blog post(s).")
        elif action == "hide":
            queryset.update(is_published=False, updated_at=timezone.now())
            messages.success(request, f"Hidden {count} blog post(s).")
        elif action == "delete":
            queryset.delete()
            messages.success(request, f"Deleted {count} blog post(s).")
        else:
            messages.error(request, "Choose a valid bulk action.")

    return redirect("dashboard:blog")


@admin_required
def blog_post_toggle_publish(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == "POST":
        post.is_published = not post.is_published
        post.save(update_fields=["is_published", "updated_at"])
        messages.success(
            request,
            "Blog post published." if post.is_published else "Blog post hidden.",
        )
    return redirect("dashboard:blog")

@admin_required
def services(request):
    items = Service.objects.all()
    return render(
        request,
        "staff/pages/services.html",
        {
            "active_page": "website",
            "services": items,
            "service_count": items.count(),
            "published_service_count": items.filter(is_published=True).count(),
        },
    )

@admin_required
def service_create(request):
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Service created.")
            return redirect("dashboard:services")
    else:
        form = ServiceForm()

    return _render_content_form(
        request,
        "staff/pages/service_form.html",
        form,
        "Add Service",
        "Create a new clinic service.",
    )

@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated.")
            return redirect("dashboard:services")
    else:
        form = ServiceForm(instance=service)

    return _render_content_form(
        request,
        "staff/pages/service_form.html",
        form,
        "Edit Service",
        "Update service details.",
    )

@admin_required
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service deleted.")
    return redirect("dashboard:services")

@admin_required
def service_toggle_publish(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        service.is_published = not service.is_published
        service.save(update_fields=["is_published", "updated_at"])
        messages.success(request, "Service published." if service.is_published else "Service hidden.")
    return redirect("dashboard:services")


@admin_required
def team_members(request):
    items = TeamMember.objects.all().order_by("sort_order", "id")
    return render(
        request,
        "staff/pages/team.html",
        {
            "active_page": "website",
            "team_members": items,
            "team_count": items.count(),
            "published_team_count": items.filter(is_published=True).count(),
        },
    )


@admin_required
def team_member_create(request):
    if request.method == "POST":
        form = TeamMemberForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Team member added.")
            return redirect("dashboard:team")
    else:
        form = TeamMemberForm()

    return _render_content_form(
        request,
        "staff/pages/team_form.html",
        form,
        "Add Team Member",
        "Add a new doctor or staff member to the clinical team list.",
    )


@admin_required
def team_member_edit(request, pk):
    member = get_object_or_404(TeamMember, pk=pk)

    if request.method == "POST":
        form = TeamMemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, "Team member updated.")
            return redirect("dashboard:team")
    else:
        form = TeamMemberForm(instance=member)

    return _render_content_form(
        request,
        "staff/pages/team_form.html",
        form,
        "Edit Team Member",
        "Update roles, bios, and publishing states.",
    )


@admin_required
def team_member_delete(request, pk):
    member = get_object_or_404(TeamMember, pk=pk)
    if request.method == "POST":
        member.delete()
        messages.success(request, "Team member deleted.")
    return redirect("dashboard:team")


@admin_required
def team_member_toggle_publish(request, pk):
    member = get_object_or_404(TeamMember, pk=pk)
    if request.method == "POST":
        member.is_published = not member.is_published
        member.save(update_fields=["is_published", "updated_at"])
        messages.success(request, "Team member shown." if member.is_published else "Team member hidden.")
    return redirect("dashboard:team")
