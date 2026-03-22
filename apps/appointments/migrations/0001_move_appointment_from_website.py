from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("patients", "0001_move_patient_from_website"),
        ("website", "0009_appointment_appointment_code_patient_patient_code"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Appointment",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=120)),
                        ("phone", models.CharField(blank=True, max_length=40)),
                        ("email", models.EmailField(blank=True, max_length=254)),
                        ("services", models.JSONField(default=list)),
                        ("date", models.DateField()),
                        ("timeslot", models.CharField(max_length=40)),
                        ("start_time", models.TimeField(blank=True, null=True)),
                        ("notes", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("appointment_code", models.CharField(blank=True, db_index=True, editable=False, max_length=16, null=True, unique=True)),
                        ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed")], default="pending", max_length=10)),
                        (
                            "patient",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="appointments",
                                to="patients.patient",
                            ),
                        ),
                    ],
                    options={
                        "ordering": ["-date", "start_time", "name"],
                        "db_table": "website_appointment",
                    },
                ),
                migrations.AddIndex(
                    model_name="appointment",
                    index=models.Index(fields=["date"], name="website_app_date_965bb0_idx"),
                ),
                migrations.AddIndex(
                    model_name="appointment",
                    index=models.Index(fields=["name"], name="website_app_name_7177d6_idx"),
                ),
                migrations.AddIndex(
                    model_name="appointment",
                    index=models.Index(fields=["patient"], name="website_app_patient_aa7552_idx"),
                ),
                migrations.AddConstraint(
                    model_name="appointment",
                    constraint=models.UniqueConstraint(
                        fields=("date", "start_time"),
                        condition=Q(status__in=["pending", "confirmed"]),
                        name="unique_active_appointment_per_timeslot",
                    ),
                ),
            ],
        ),
    ]
