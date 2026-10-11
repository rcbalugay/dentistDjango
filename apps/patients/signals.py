import logging
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.shared.middleware import get_current_user, get_current_request
from .models import Patient, PatientDocument, AuditLog
from .storage import get_protected_storage

logger = logging.getLogger(__name__)


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _delete_storage_file(storage, file_name):
    """Safely delete a file from protected storage, logging errors without crashing."""
    if not file_name:
        return
    try:
        if storage.exists(file_name):
            storage.delete(file_name)
            logger.info("Successfully deleted protected file from storage: %s", file_name)
    except Exception as exc:
        logger.warning("Failed to delete protected file '%s' from storage: %s", file_name, exc)


@receiver(post_save, sender=Patient)
def audit_patient_save(sender, instance, created, **kwargs):
    # Prevent duplicate logging when Django auto-saves the generated patient_code immediately after creation
    update_fields = kwargs.get("update_fields")
    if update_fields and "patient_code" in update_fields:
        create_log = AuditLog.objects.filter(model_name="Patient", object_id=instance.id, action=AuditLog.ACTION_CREATE).first()
        if create_log:
            create_log.description = f"Patient record created for {instance.name} (Code: {instance.patient_code})"
            create_log.save(update_fields=["description"])
            return

    user = get_current_user()
    request = get_current_request()
    ip = get_client_ip(request)
    
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    desc = f"Patient record {'created' if created else 'updated'} for {instance.name} (Code: {instance.patient_code or 'pending'})"
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name="Patient",
        object_id=instance.id,
        description=desc,
        ip_address=ip
    )


@receiver(post_delete, sender=Patient)
def audit_patient_delete(sender, instance, **kwargs):
    user = get_current_user()
    request = get_current_request()
    ip = get_client_ip(request)
    
    desc = f"Patient record deleted for {instance.name} (Code: {instance.patient_code})"
    
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_DELETE,
        model_name="Patient",
        object_id=instance.id,
        description=desc,
        ip_address=ip
    )


@receiver(post_save, sender=PatientDocument)
def patient_document_post_save(sender, instance, created, **kwargs):
    # 1. Audit log on creation
    if created:
        user = get_current_user()
        request = get_current_request()
        ip = get_client_ip(request)
        patient_name = (
            getattr(instance.patient, "name", "unknown")
            if hasattr(instance, "patient") and instance.patient
            else "unknown"
        )
        desc = f"Patient document uploaded: {instance.title} ({instance.get_document_type_display()}) for patient {patient_name}"
        AuditLog.objects.create(
            user=user,
            action=AuditLog.ACTION_CREATE,
            model_name="PatientDocument",
            object_id=instance.id,
            description=desc,
            ip_address=ip
        )

    # 2. File replacement cleanup
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "file" not in update_fields:
        return

    old_file_name = getattr(instance, "_original_file_name", None)
    new_file_name = instance.file.name if instance.file else None

    if old_file_name and new_file_name and old_file_name != new_file_name:
        storage = get_protected_storage()
        using = kwargs.get("using")

        def _cleanup():
            _delete_storage_file(storage, old_file_name)

        transaction.on_commit(_cleanup, using=using)
        # Update remembered key to prevent duplicate cleanup on repeated saves
        instance._original_file_name = new_file_name


@receiver(post_delete, sender=PatientDocument)
def patient_document_post_delete(sender, instance, **kwargs):
    # 1. Audit log on deletion
    user = get_current_user()
    request = get_current_request()
    ip = get_client_ip(request)
    patient_name = (
        getattr(instance.patient, "name", "unknown")
        if hasattr(instance, "patient") and instance.patient
        else "unknown"
    )
    desc = f"Patient document deleted: {instance.title} for patient {patient_name}"
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_DELETE,
        model_name="PatientDocument",
        object_id=instance.id,
        description=desc,
        ip_address=ip
    )

    # 2. Physical file cleanup on commit (covers single, queryset, and patient cascade delete)
    if instance.file and instance.file.name:
        file_name = instance.file.name
        storage = get_protected_storage()
        using = kwargs.get("using")

        def _cleanup():
            _delete_storage_file(storage, file_name)

        transaction.on_commit(_cleanup, using=using)
