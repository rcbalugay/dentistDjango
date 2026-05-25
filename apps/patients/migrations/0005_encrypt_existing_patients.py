import os
from django.db import migrations
from cryptography.fernet import Fernet

def encrypt_data(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    
    key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not key:
        # Fallback dummy key for testing
        key = Fernet.generate_key()
    elif isinstance(key, str):
        key = key.encode()
    
    fernet = Fernet(key)

    for patient in Patient.objects.all():
        modified = False
        
        # Phone encryption
        if patient.phone and not patient.phone.startswith("gAAAA"):
            patient.phone = fernet.encrypt(patient.phone.encode()).decode()
            modified = True
            
        # Email encryption
        if patient.email and not patient.email.startswith("gAAAA"):
            patient.email = fernet.encrypt(patient.email.encode()).decode()
            modified = True
            
        # Notes encryption
        if patient.notes and not patient.notes.startswith("gAAAA"):
            patient.notes = fernet.encrypt(patient.notes.encode()).decode()
            modified = True
            
        if modified:
            patient.save(update_fields=["phone", "email", "notes"])

def decrypt_data(apps, schema_editor):
    Patient = apps.get_model("patients", "Patient")
    
    key = os.getenv("FIELD_ENCRYPTION_KEY")
    if not key:
        return
    elif isinstance(key, str):
        key = key.encode()
    
    fernet = Fernet(key)

    for patient in Patient.objects.all():
        modified = False
        
        # Phone decryption
        if patient.phone and patient.phone.startswith("gAAAA"):
            try:
                patient.phone = fernet.decrypt(patient.phone.encode()).decode()
                modified = True
            except Exception:
                pass
                
        # Email decryption
        if patient.email and patient.email.startswith("gAAAA"):
            try:
                patient.email = fernet.decrypt(patient.email.encode()).decode()
                modified = True
            except Exception:
                pass
                
        # Notes decryption
        if patient.notes and patient.notes.startswith("gAAAA"):
            try:
                patient.notes = fernet.decrypt(patient.notes.encode()).decode()
                modified = True
            except Exception:
                pass
                
        if modified:
            patient.save(update_fields=["phone", "email", "notes"])

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0004_remove_patient_website_pat_phone_6e57b7_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(encrypt_data, decrypt_data),
    ]
