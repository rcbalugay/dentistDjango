from pathlib import Path
from django.db import migrations
from django.db.models import Count, F


def backfill_and_demote_duplicate_insurance(apps, schema_editor):
    PatientDocument = apps.get_model("patients", "PatientDocument")

    # 1. Backfill blank original_filename from stored filename as a legacy display fallback
    for doc in PatientDocument.objects.filter(original_filename="").exclude(file=""):
        if doc.file and doc.file.name:
            doc.original_filename = Path(doc.file.name).name[:255]
            doc.save(update_fields=["original_filename"])

    # 2. Identify patients with multiple insurance records and deterministically demote older duplicates
    duplicate_patient_ids = (
        PatientDocument.objects.filter(document_type="insurance")
        .values("patient_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("patient_id", flat=True)
    )

    for patient_id in duplicate_patient_ids:
        insurance_docs = list(
            PatientDocument.objects.filter(
                patient_id=patient_id,
                document_type="insurance",
            ).order_by(
                F("uploaded_at").desc(nulls_last=True),
                F("id").desc(),
            )
        )

        # Keep the newest record as active; demote older duplicates to 'other'
        for older_doc in insurance_docs[1:]:
            older_doc.document_type = "other"
            base_title = older_doc.title or "Insurance"
            older_doc.title = f"[Archived Insurance] {base_title}"[:150]
            older_doc.save(update_fields=["document_type", "title"])


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0007_patientdocument_original_filename_and_upload_to"),
    ]

    operations = [
        migrations.RunPython(
            backfill_and_demote_duplicate_insurance,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
