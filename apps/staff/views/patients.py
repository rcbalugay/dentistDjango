from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Max, Min, Q
from django.http import JsonResponse, FileResponse, Http404
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


def get_patient_queue(patient_qs, sort="all"):
    """
    Retrieves the patient queue, annotated with last_seen for sorting,
    filtering for patients with at least one appointment.
    """
    patient_queue_qs = (
        patient_qs.filter(appointments__isnull=False)
        .annotate(last_seen=Max("appointments__date"))
        .distinct()
    )
    if sort == "newest":
        patient_queue_qs = patient_queue_qs.order_by("-created_at", "name")
    elif sort == "oldest":
        patient_queue_qs = patient_queue_qs.order_by("created_at", "name")
    else:
        patient_queue_qs = patient_queue_qs.order_by("-last_seen", "name")
    return list(patient_queue_qs)


def get_patient_appointment_stats(selected_patient, selected_appointments):
    """
    Computes appointment statistics for a single selected patient.
    """
    stats = selected_appointments.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Appointment.STATUS_PENDING)),
        confirmed=Count("id", filter=Q(status=Appointment.STATUS_CONFIRMED)),
        completed=Count("id", filter=Q(status=Appointment.STATUS_COMPLETED)),
        cancelled=Count("id", filter=Q(status=Appointment.STATUS_CANCELLED)),
    )
    
    completed = stats["completed"]
    total = stats["total"]
    pending = stats["pending"]
    confirmed = stats["confirmed"]
    cancelled = stats["cancelled"]
    
    adherence = round((completed * 100.0 / total), 1) if total else 0
    return {
        "total": total,
        "completed": completed,
        "upcoming": pending + confirmed,
        "cancelled": cancelled,
        "adherence": adherence,
    }


def get_patient_documents(selected_patient):
    """
    Retrieves all documents for a patient in a single query,
    splitting them into insurance and non-insurance lists.
    """
    all_docs = list(selected_patient.documents.all())
    insurance_document = next((d for d in all_docs if d.document_type == PatientDocument.TYPE_INSURANCE), None)
    document_items = [d for d in all_docs if d.document_type != PatientDocument.TYPE_INSURANCE]
    return insurance_document, document_items


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
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Select a patient before uploading a file."})
            messages.error(request, "Select a patient before uploading a file.")
            return redirect(patients_url(query=q, sort=sort))

        if action == "upload_insurance":
            insurance_file = request.FILES.get("insurance_file")
            insurance_title = request.POST.get("insurance_title", "").strip() or "Insurance attachment"
            if not insurance_file:
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "Choose an insurance image or file to upload."})
                messages.error(request, "Choose an insurance image or file to upload.")
            else:
                form_data = {
                    "title": insurance_title,
                    "document_type": PatientDocument.TYPE_INSURANCE,
                }
                form_files = {
                    "file": insurance_file,
                }
                insurance_form = PatientDocumentForm(form_data, form_files)
                if insurance_form.is_valid():
                    doc = insurance_form.save(commit=False)
                    doc.patient = target_patient
                    doc.save()
                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({
                            "success": True,
                            "message": "Insurance attachment uploaded.",
                            "file_url": reverse("dashboard:download_patient_document", args=[doc.id]),
                            "filename": doc.filename,
                            "title": doc.title,
                            "is_image": doc.is_image,
                            "uploaded_at": doc.uploaded_at.strftime("%d %b %Y")
                        })
                    messages.success(request, "Insurance attachment uploaded.")
                else:
                    first_error = next(iter(insurance_form.errors.values()))[0] if insurance_form.errors else "Choose an insurance image or file to upload."
                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse({"success": False, "error": first_error})
                    messages.error(request, first_error)
            return redirect(patients_url(patient_id=target_patient.id, query=q, sort=sort))

        if action == "upload_document":
            document_form = PatientDocumentForm(request.POST, request.FILES, prefix="doc")
            if document_form.is_valid():
                document = document_form.save(commit=False)
                document.patient = target_patient
                document.save()
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    from django.template.defaultfilters import filesizeformat
                    return JsonResponse({
                        "success": True,
                        "message": "Patient document uploaded.",
                        "file_url": reverse("dashboard:download_patient_document", args=[document.id]),
                        "filename": document.filename,
                        "title": document.title,
                        "is_image": document.is_image,
                        "doc_type": document.get_document_type_display(),
                        "size": filesizeformat(document.file.size),
                        "uploaded_at": document.uploaded_at.strftime("%d %b %Y")
                    })
                messages.success(request, "Patient document uploaded.")
                return redirect(patients_url(patient_id=target_patient.id, query=q, sort=sort))
            
            first_error = next(iter(document_form.errors.values()))[0] if document_form.errors else "Please complete the document upload form."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": first_error})
            messages.error(request, first_error)

    patient_qs = Patient.objects.all()
    if q:
        patient_qs = patient_qs.filter(
            Q(name__icontains=q)
            | Q(patient_code__icontains=q)
        )

    patient_queue = get_patient_queue(patient_qs, sort=sort)

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

        quick_stats = get_patient_appointment_stats(selected_patient, selected_appointments)
        insurance_document, document_items = get_patient_documents(selected_patient)

        # Log VIEW action in AuditLog
        from apps.patients.models import AuditLog
        from apps.patients.signals import get_client_ip
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.ACTION_VIEW,
            model_name="Patient",
            object_id=selected_patient.id,
            description=f"Accessed profile for patient {selected_patient.name} (Code: {selected_patient.patient_code or 'pending'}) via staff panel.",
            ip_address=get_client_ip(request)
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


@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def download_patient_document(request, pk):
    """
    Securely streams a patient document file after verifying authentication
    and staff authorization status.
    """
    try:
        document = PatientDocument.objects.select_related("patient").get(pk=pk)
    except PatientDocument.DoesNotExist:
        raise Http404("Document does not exist.")

    # Log VIEW action to the AuditLog
    from apps.patients.models import AuditLog
    from apps.patients.signals import get_client_ip
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=AuditLog.ACTION_VIEW,
        model_name="PatientDocument",
        object_id=document.id,
        description=f"Downloaded/Opened document {document.title} ({document.get_document_type_display()}) for patient {document.patient.name}.",
        ip_address=get_client_ip(request)
    )
    
    try:
        response = FileResponse(document.file.open("rb"))
        # Set content-type cleanly or let FileResponse infer it
        return response
    except FileNotFoundError:
        raise Http404("File not found on storage disk.")

