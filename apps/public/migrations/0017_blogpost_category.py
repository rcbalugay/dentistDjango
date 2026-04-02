from django.db import migrations, models


def seed_blog_categories(apps, schema_editor):
    BlogPost = apps.get_model("public", "BlogPost")
    category_map = {
        "how-often-should-you-schedule-a-professional-cleaning": "preventive-care",
        "what-to-expect-at-your-childs-first-dental-visit": "pediatric-dentistry",
        "when-it-may-be-time-to-ask-about-braces": "orthodontics",
    }

    for slug, category in category_map.items():
        BlogPost.objects.filter(slug=slug).update(category=category)


def reset_blog_categories(apps, schema_editor):
    BlogPost = apps.get_model("public", "BlogPost")
    BlogPost.objects.filter(
        slug__in=[
            "how-often-should-you-schedule-a-professional-cleaning",
            "what-to-expect-at-your-childs-first-dental-visit",
            "when-it-may-be-time-to-ask-about-braces",
        ]
    ).update(category="clinic-updates")


class Migration(migrations.Migration):

    dependencies = [
        ("public", "0016_seed_testimonials_and_blog_posts"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogpost",
            name="category",
            field=models.CharField(
                choices=[
                    ("preventive-care", "Preventive Care"),
                    ("pediatric-dentistry", "Pediatric Dentistry"),
                    ("orthodontics", "Orthodontics"),
                    ("restorative-dentistry", "Restorative Dentistry"),
                    ("clinic-updates", "Clinic Updates"),
                ],
                default="clinic-updates",
                max_length=40,
            ),
        ),
        migrations.RunPython(seed_blog_categories, reset_blog_categories),
    ]
