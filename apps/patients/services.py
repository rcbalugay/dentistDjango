from apps.patients.models import Patient
from .normalization import normalize_phone, normalize_email
from .selectors import resolve_patient_identity, PatientConflictError


def get_or_create_patient_record(*, name="", phone="", email=""):
    norm_phone = normalize_phone(phone)
    norm_email = normalize_email(email)
    clean_name = name.strip() if name else ""

    # Business rule: atleast one contact identifier (phone or email) is required
    if not norm_email and not norm_phone:
        return None
    
    patient = resolve_patient_identity(name=clean_name, phone=norm_phone, email=norm_email)

    if not patient:
        patient = Patient.objects.create(
            name=clean_name,
            phone=norm_phone,
            email=norm_email,
        )
        return patient

    # Safe update: never overwrite existing populated contact identifiers automatically
    changed_fields = []
    if clean_name and patient.name != clean_name:
        patient.name = clean_name
        changed_fields.append("name")

    # Only fill if the patient previously had no phone
    if norm_phone and not patient.phone:
        patient.phone = norm_phone
        changed_fields.append("phone")

    # Only fill if the patient previously had no email
    if norm_email and not patient.email:
        patient.email = norm_email
        changed_fields.append("email")

    if changed_fields:
        patient.save(update_fields=changed_fields)
        
    return patient
