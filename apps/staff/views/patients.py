from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Max, Min, Q
from django.shortcuts import render
from django.utils import timezone

from website.models import Appointment, Patient

from .auth import staff_only

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def patients(request):
    q = request.GET.get("q", "").strip()
    selected_key = request.GET.get("patient", "").strip()
    today = timezone.localdate()

    patient_qs = Patient.objects.all()
    if q:
        patient_qs = patient_qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
        )

    patient_queue = list(
        patient_qs.annotate(
            first_seen=Min("appointments__created_at"),
            last_seen=Max("appointments__date"),
            total_appointments=Count("appointments", distinct=True),
            pending_count=Count(
                "appointments",
                filter=Q(appointments__status=Appointment.STATUS_PENDING),
                distinct=True,
            ),
            confirmed_count=Count(
                "appointments",
                filter=Q(appointments__status=Appointment.STATUS_CONFIRMED),
                distinct=True,
            ),
            completed_count=Count(
                "appointments",
                filter=Q(appointments__status=Appointment.STATUS_COMPLETED),
                distinct=True,
            ),
            cancelled_count=Count(
                "appointments",
                filter=Q(appointments__status=Appointment.STATUS_CANCELLED),
                distinct=True,
            ),
        )
        .filter(total_appointments__gt=0)
        .order_by("-last_seen", "name")
    )

    selected_patient = None
    upcoming_schedule = []
    visit_history = []
    document_items = []
    quick_stats = {
        "total": 0,
        "completed": 0,
        "upcoming": 0,
        "cancelled": 0,
        "adherence": 0,
    }
    assurance_card = {
        "member_number": "",
        "status": "New",
        "expiry": today,
    }

    if patient_queue:
        selected_patient = patient_queue[0]
        if selected_key.isdigit():
            wanted = int(selected_key)
            selected_patient = next((p for p in patient_queue if p.id == wanted), selected_patient)

        selected_appointments = (
            Appointment.objects.filter(patient=selected_patient)
            .order_by("-date", "-start_time")
        )

        upcoming_schedule = list(
            selected_appointments.filter(
                date__gte=today,
                status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
            ).order_by("date", "start_time")[:6]
        )
        visit_history = list(selected_appointments[:8])

        completed = selected_patient.completed_count
        total = selected_patient.total_appointments
        pending = selected_patient.pending_count
        confirmed = selected_patient.confirmed_count
        cancelled = selected_patient.cancelled_count

        adherence = round((completed * 100.0 / total), 1) if total else 0
        quick_stats = {
            "total": total,
            "completed": completed,
            "upcoming": pending + confirmed,
            "cancelled": cancelled,
            "adherence": adherence,
        }

        assurance_card = {
            "member_number": selected_patient.patient_code,
            "status": "Active" if completed > 0 else "New",
            "expiry": today + timedelta(days=365),
        }

        for a in visit_history[:4]:
            services_label = ", ".join(a.services) if a.services else "General dental service"
            note_words = len((a.notes or "").split())
            document_items.append({
                "title": f"Visit summary {a.appointment_code}",
                "subtitle": services_label,
                "meta": f"{a.date:%d %b %Y} - {note_words} note words",
                "status": a.get_status_display(),
            })

    return render(request, "staff/pages/patients.html", {
        "active_page": "patients",
        "q": q,
        "today": today,
        "patient_queue": patient_queue,
        "selected_patient": selected_patient,
        "upcoming_schedule": upcoming_schedule,
        "visit_history": visit_history,
        "document_items": document_items,
        "quick_stats": quick_stats,
        "assurance_card": assurance_card,
    })
