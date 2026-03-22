from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("website", "0009_appointment_appointment_code_patient_patient_code"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Patient",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=120)),
                        ("phone", models.CharField(blank=True, max_length=40)),
                        ("email", models.EmailField(blank=True, max_length=254)),
                        ("notes", models.TextField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("patient_code", models.CharField(blank=True, db_index=True, editable=False, max_length=16, null=True, unique=True)),
                    ],
                    options={
                        "ordering": ["name"],
                        "db_table": "website_patient",
                    },
                ),
                migrations.AddIndex(
                    model_name="patient",
                    index=models.Index(fields=["name"], name="website_pat_name_d318b7_idx"),
                ),
                migrations.AddIndex(
                    model_name="patient",
                    index=models.Index(fields=["phone"], name="website_pat_phone_6e57b7_idx"),
                ),
                migrations.AddIndex(
                    model_name="patient",
                    index=models.Index(fields=["email"], name="website_pat_email_148a3f_idx"),
                ),
            ],
        ),
    ]
