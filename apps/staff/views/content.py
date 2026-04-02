from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.public.models import BlogPost, Testimonial
from apps.staff.forms import BlogPostForm, TestimonialForm

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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def testimonial_delete(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    if request.method == "POST":
        testimonial.delete()
        messages.success(request, "Testimonial deleted.")
    return redirect("dashboard:testimonials")


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def blog_post_delete(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Blog post deleted.")
    return redirect("dashboard:blog")


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
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
