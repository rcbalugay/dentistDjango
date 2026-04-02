from datetime import datetime

from django.db import migrations
from django.utils import timezone


def seed_content(apps, schema_editor):
    Testimonial = apps.get_model("public", "Testimonial")
    BlogPost = apps.get_model("public", "BlogPost")

    testimonials = [
        {
            "patient_name": "Ana R.",
            "visit_label": "Routine cleaning patient",
            "quote": "The team explained every step clearly and made the entire visit feel calm from start to finish.",
            "sort_order": 1,
        },
        {
            "patient_name": "Parent Feedback",
            "visit_label": "Pediatric visit",
            "quote": "Our child's first appointment felt warm and well-paced, which made the whole experience easier for us.",
            "sort_order": 2,
        },
        {
            "patient_name": "Marco T.",
            "visit_label": "Treatment consultation",
            "quote": "I appreciated how organized the clinic was and how thoughtfully the treatment plan was explained.",
            "sort_order": 3,
        },
        {
            "patient_name": "Liza C.",
            "visit_label": "Restorative care patient",
            "quote": "From scheduling to aftercare instructions, everything felt clear, respectful, and easy to follow.",
            "sort_order": 4,
        },
    ]

    for item in testimonials:
        Testimonial.objects.get_or_create(
            patient_name=item["patient_name"],
            sort_order=item["sort_order"],
            defaults={
                "visit_label": item["visit_label"],
                "quote": item["quote"],
                "is_published": True,
            },
        )

    blog_posts = [
        {
            "title": "How often should you schedule a professional cleaning?",
            "slug": "how-often-should-you-schedule-a-professional-cleaning",
            "excerpt": "Understand what affects cleaning frequency and why regular preventive visits matter even when nothing hurts.",
            "body": (
                "Professional cleanings help remove buildup that daily brushing cannot fully handle. "
                "For many patients, every six months is a good baseline, but gum health, restorations, braces, "
                "and past dental history can change that rhythm.\n\n"
                "If bleeding gums, tartar buildup, or sensitivity show up between visits, it is worth asking your dentist "
                "whether a shorter interval makes more sense for your case."
            ),
            "published_at": timezone.make_aware(datetime(2026, 4, 5, 9, 0)),
        },
        {
            "title": "What to expect at your child's first dental visit",
            "slug": "what-to-expect-at-your-childs-first-dental-visit",
            "excerpt": "Here is a simple look at how we help young patients feel safe, prepared, and comfortable on day one.",
            "body": (
                "A first visit is usually short, gentle, and focused on helping a child feel familiar with the clinic. "
                "We look at oral development, talk through brushing habits, and answer the questions parents most often ask.\n\n"
                "The goal is not only to check teeth, but to build trust early so future visits feel normal instead of stressful."
            ),
            "published_at": timezone.make_aware(datetime(2026, 3, 22, 10, 0)),
        },
        {
            "title": "When it may be time to ask about braces",
            "slug": "when-it-may-be-time-to-ask-about-braces",
            "excerpt": "Spacing, bite changes, and crowding can show up gradually. These are a few early signs worth discussing.",
            "body": (
                "Orthodontic concerns do not always begin with a dramatic change. Crowding, early bite shifts, "
                "or difficulty cleaning between overlapping teeth can all be signs that it is time for an evaluation.\n\n"
                "An early consultation does not always mean treatment starts immediately, but it gives families a clearer timeline "
                "and helps avoid surprises later."
            ),
            "published_at": timezone.make_aware(datetime(2026, 3, 11, 8, 30)),
        },
    ]

    for item in blog_posts:
        BlogPost.objects.get_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "excerpt": item["excerpt"],
                "body": item["body"],
                "author_name": "Clinic Team",
                "published_at": item["published_at"],
                "is_published": True,
            },
        )


def unseed_content(apps, schema_editor):
    Testimonial = apps.get_model("public", "Testimonial")
    BlogPost = apps.get_model("public", "BlogPost")

    Testimonial.objects.filter(
        patient_name__in=["Ana R.", "Parent Feedback", "Marco T.", "Liza C."]
    ).delete()
    BlogPost.objects.filter(
        slug__in=[
            "how-often-should-you-schedule-a-professional-cleaning",
            "what-to-expect-at-your-childs-first-dental-visit",
            "when-it-may-be-time-to-ask-about-braces",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("public", "0015_blogpost_testimonial"),
    ]

    operations = [
        migrations.RunPython(seed_content, unseed_content),
    ]
