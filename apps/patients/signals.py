from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.shared.middleware import get_current_user, get_current_request
from .models import Patient, PatientDocument, AuditLog

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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
def audit_document_save(sender, instance, created, **kwargs):
    if not created:
        return
        
    user = get_current_user()
    request = get_current_request()
    ip = get_client_ip(request)
    
    desc = f"Patient document uploaded: {instance.title} ({instance.get_document_type_display()}) for patient {instance.patient.name}"
    
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_CREATE,
        model_name="PatientDocument",
        object_id=instance.id,
        description=desc,
        ip_address=ip
    )

@receiver(post_delete, sender=PatientDocument)
def audit_document_delete(sender, instance, **kwargs):
    user = get_current_user()
    request = get_current_request()
    ip = get_client_ip(request)
    
    desc = f"Patient document deleted: {instance.title} for patient {instance.patient.name}"
    
    AuditLog.objects.create(
        user=user,
        action=AuditLog.ACTION_DELETE,
        model_name="PatientDocument",
        object_id=instance.id,
        description=desc,
        ip_address=ip
    )
