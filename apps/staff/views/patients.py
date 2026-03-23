from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Max, Min, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.patients.forms import PatientDocumentForm
from apps.patients.models import Patient, PatientDocument

from .auth import staff_only


PATIENT_QUEUE_SORT_OPTIONS = {"all", "newest", "oldest"}


def patients_url(*, patient_id=None, query="", sort="all"):
    params = {}
    if query:
        params["q"] = query
    if sort and sort != "all":
        params["sort"] = sort
    if patient_id:
        params["patient"] = patient_id
    base_url = reverse("dashboard:patients")
    return f"{base_url}?{urlencode(params)}" if params else base_url


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def patients(request):
    q = ((request.POST.get("q") if request.method == "POST" else request.GET.get("q", "")) or "").strip()
    sort = ((request.POST.get("sort") if request.method == "POST" else request.GET.get("sort", "all")) or "all").strip().lower()
    if sort not in PATIENT_QUEUE_SORT_OPTIONS:
        sort = "all"
    selected_key = request.GET.get("patient", "").strip()
    today = timezone.localdate()
    document_form = PatientDocumentForm(prefix="doc")

    if request.method == "POST":
        selected_key = request.POST.get("patient_id", "").strip() or selected_key
        target_patient = Patient.objects.filter(id=selected_key).first() if selected_key.isdigit() else None
        action = request.POST.get("document_action", "")

        if not target_patient:
            messages.error(request, "Select a patient before uploading a file.")
            return redirect(patients_url(query=q, sort=sort))

        if action == "upload_insurance":
            insurance_file = request.FILES.get("insurance_file")
            insurance_title = request.POST.get("insurance_title", "").strip() or "Insurance attachment"
            if not insurance_file:
                messages.error(request, "Choose an insurance image or file to upload.")
            else:
                PatientDocument.objects.create(
                    patient=target_patient,
                    title=insurance_title,
                    document_type=PatientDocument.TYPE_INSURANCE,
                    file=insurance_file,
                )
                messages.success(request, "Insurance attachment uploaded.")
            return redirect(patients_url(patient_id=target_patient.id, query=q, sort=sort))

        if action == "upload_document":
            document_form = PatientDocumentForm(request.POST, request.FILES, prefix="doc")
            if document_form.is_valid():
                document = document_form.save(commit=False)
                document.patient = target_patient
                document.save()
                messages.success(request, "Patient document uploaded.")
                return redirect(patients_url(patient_id=target_patient.id, query=q, sort=sort))
            messages.error(request, "Please complete the document upload form.")

    patient_qs = Patient.objects.all()
    if q:
        patient_qs = patient_qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
        )

    patient_queue_qs = (
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
    )

    if sort == "newest":
        patient_queue_qs = patient_queue_qs.order_by("-created_at", "name")
    elif sort == "oldest":
        patient_queue_qs = patient_queue_qs.order_by("created_at", "name")
    else:
        patient_queue_qs = patient_queue_qs.order_by("-last_seen", "name")

    patient_queue = list(patient_queue_qs)

    selected_patient = None
    upcoming_schedule = []
    visit_history = []
    document_items = []
    insurance_document = None
    quick_stats = {
        "total": 0,
        "completed": 0,
        "upcoming": 0,
        "cancelled": 0,
        "adherence": 0,
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

        insurance_document = selected_patient.documents.filter(
            document_type=PatientDocument.TYPE_INSURANCE
        ).first()
        document_items = list(
            selected_patient.documents.exclude(document_type=PatientDocument.TYPE_INSURANCE)
        )

    return render(request, "staff/pages/patients.html", {
        "active_page": "patients",
        "q": q,
        "sort": sort,
        "today": today,
        "patient_queue": patient_queue,
        "selected_patient": selected_patient,
        "upcoming_schedule": upcoming_schedule,
        "visit_history": visit_history,
        "document_items": document_items,
        "insurance_document": insurance_document,
        "quick_stats": quick_stats,
        "document_form": document_form,
    })
