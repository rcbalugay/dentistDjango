import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.public.models import SiteContent, Testimonial, BlogPost, Service, TeamMember

def compress_and_convert_to_webp(image_field, max_width=1200, max_height=1200, quality=82):
    if not image_field:
        return
    
    try:
        # Check if already a WebP image
        if image_field.name.endswith(".webp"):
            return
            
        # Open using Pillow
        img = Image.open(image_field)
        
        # Normalize RGBA and transparency
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGBA", img.size, (255, 255, 255, 0))
            background.paste(img, (0, 0), img.convert("RGBA"))
            img = background
        else:
            img = img.convert("RGB")
            
        # Scale if it exceeds dimensions
        width, height = img.size
        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        # Convert and compress
        output = BytesIO()
        img.save(output, format="WEBP", quality=quality)
        output.seek(0)
        
        # Build new filename
        original_name = os.path.basename(image_field.name)
        name_without_ext = os.path.splitext(original_name)[0]
        new_filename = f"{name_without_ext}.webp"
        
        # Save back to field (save=False to prevent recursive save signals)
        image_field.save(new_filename, ContentFile(output.read()), save=False)
    except Exception as e:
        # Graceful fallback: do nothing if it fails
        pass

@receiver(pre_save, sender=SiteContent)
def optimize_site_content_images(sender, instance, **kwargs):
    # SiteContent has multiple ImageFields
    image_fields = [
        "hero_slide_1_background",
        "hero_slide_2_background",
        "home_intro_background",
        "about_side_image",
        "about_founder_photo",
        "page_banner_background",
    ]
    for field_name in image_fields:
        field = getattr(instance, field_name)
        if field:
            # Check if this is a newly uploaded file
            try:
                db_instance = SiteContent.objects.get(pk=instance.pk)
                db_field = getattr(db_instance, field_name)
            except SiteContent.DoesNotExist:
                db_field = None
                
            if not db_field or field != db_field:
                compress_and_convert_to_webp(field, max_width=1600, max_height=1600)

@receiver(pre_save, sender=Testimonial)
def optimize_testimonial_images(sender, instance, **kwargs):
    if instance.photo:
        try:
            db_instance = Testimonial.objects.get(pk=instance.pk)
            db_field = db_instance.photo
        except Testimonial.DoesNotExist:
            db_field = None
            
        if not db_field or instance.photo != db_field:
            compress_and_convert_to_webp(instance.photo, max_width=600, max_height=600)

@receiver(pre_save, sender=BlogPost)
def optimize_blog_images(sender, instance, **kwargs):
    if instance.image:
        try:
            db_instance = BlogPost.objects.get(pk=instance.pk)
            db_field = db_instance.image
        except BlogPost.DoesNotExist:
            db_field = None
            
        if not db_field or instance.image != db_field:
            compress_and_convert_to_webp(instance.image, max_width=1000, max_height=1000)

@receiver(pre_save, sender=Service)
def optimize_service_images(sender, instance, **kwargs):
    if instance.image:
        try:
            db_instance = Service.objects.get(pk=instance.pk)
            db_field = db_instance.image
        except Service.DoesNotExist:
            db_field = None
            
        if not db_field or instance.image != db_field:
            compress_and_convert_to_webp(instance.image, max_width=800, max_height=800)


@receiver(pre_save, sender=TeamMember)
def optimize_team_images(sender, instance, **kwargs):
    if instance.photo:
        try:
            db_instance = TeamMember.objects.get(pk=instance.pk)
            db_field = db_instance.photo
        except TeamMember.DoesNotExist:
            db_field = None
            
        if not db_field or instance.photo != db_field:
            compress_and_convert_to_webp(instance.photo, max_width=600, max_height=600)
