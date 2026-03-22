from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_move_patient_from_website"),
        ("appointments", "0001_move_appointment_from_website"),
        ("website", "0009_appointment_appointment_code_patient_patient_code"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Appointment"),
                migrations.DeleteModel(name="Patient"),
            ],
        ),
    ]
