from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Appointment, Patient
from .constants import (
    APPOINTMENT_SERVICES,
    CLINIC_OPEN_WEEKDAYS,
    CLINIC_OPEN_DAYS_LABEL,
    CLINIC_SLOT_TIME_SET,
    SAME_DAY_BOOKING_CUTOFF_HOURS,
    CLINIC_HOLIDAYS,
)

class BaseAppointmentForm(forms.ModelForm):
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    appointment_time = forms.TimeField(
        input_formats=["%I:%M %p", "%I:%M%p", "%H:%M"],
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    services = forms.MultipleChoiceField(
        choices=[(s, s) for s in APPOINTMENT_SERVICES],
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = Appointment
        fields = ["name", "phone", "email", "appointment_date", "appointment_time", "services", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def validate_slot_collision(self, cleaned):
        appt_date = cleaned.get("appointment_date")
        appt_time = cleaned.get("appointment_time")

        if not appt_date or not appt_time:
            return cleaned

        timeslot_str = appt_time.strftime("%I:%M %p").lstrip("0")
        cleaned["timeslot_str"] = timeslot_str

        qs = Appointment.objects.filter(
            date=appt_date,
            start_time=appt_time,
            status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
        )

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "The selected date or time is already booked. Please choose a different date or time."
            )

        return cleaned

    def save(self, commit=True, status=None):
        instance = super().save(commit=False)

        date_obj = self.cleaned_data["appointment_date"]
        time_obj = self.cleaned_data["appointment_time"]

        timeslot_str = self.cleaned_data.get("timeslot_str") or time_obj.strftime("%I:%M %p").lstrip("0")

        instance.date = date_obj
        instance.start_time = time_obj
        instance.timeslot = timeslot_str

        services = self.cleaned_data.get("services") or []
        services = sorted({s.strip() for s in services if s.strip()})
        instance.services = services

        name = self.cleaned_data.get("name", "").strip()
        phone = self.cleaned_data.get("phone", "").strip()
        email = self.cleaned_data.get("email", "").strip()

        patient = None

        if phone:
            patient = Patient.objects.filter(phone=phone).first()

        if not patient and email:
            patient = Patient.objects.filter(email=email).first()

        if not patient and name:
            patient = Patient.objects.filter(name__iexact=name, phone=phone, email=email).first()

        if not patient and (name or phone or email):
            patient = Patient.objects.create(
                name=name,
                phone=phone,
                email=email,
            )

        if patient:
            instance.patient = patient

        if status is not None:
            instance.status = status

        if commit:
            instance.save()

        return instance


class AppointmentForm(BaseAppointmentForm):
    def clean(self):
        cleaned = super().clean()
        appt_date = cleaned.get("appointment_date")
        appt_time = cleaned.get("appointment_time")

        if not appt_date or not appt_time:
            return cleaned

        today = timezone.localdate()

        if appt_date < today:
            self.add_error("appointment_date", "Please choose today or a future date.")

        if appt_date.weekday() not in CLINIC_OPEN_WEEKDAYS:
            self.add_error(
                "appointment_date",
                f"Appointments are only available on {CLINIC_OPEN_DAYS_LABEL}.",
            )

        holiday_name = CLINIC_HOLIDAYS.get(appt_date)
        if holiday_name:
            self.add_error(
                "appointment_date",
                f"Appointments are not available on {holiday_name}.",
            )

        if appt_time not in CLINIC_SLOT_TIME_SET:
            self.add_error(
                "appointment_time",
                "Appointments are available only on the hour from 9:00 AM to 5:00 PM.",
            )

        if self.errors:
            return cleaned

        appointment_dt = timezone.make_aware(
            datetime.combine(appt_date, appt_time),
            timezone.get_current_timezone(),
        )
        cutoff_dt = timezone.now() + timedelta(hours=SAME_DAY_BOOKING_CUTOFF_HOURS)

        if appointment_dt < cutoff_dt:
            self.add_error(
                "appointment_time",
                f"Appointments must be booked at least {SAME_DAY_BOOKING_CUTOFF_HOURS} hours in advance.",
            )

        if self.errors:
            return cleaned

        self.validate_slot_collision(cleaned)
        return cleaned

class StaffAppointmentForm(BaseAppointmentForm):
    def clean(self):
        cleaned = super().clean()
        appt_date = cleaned.get("appointment_date")
        appt_time = cleaned.get("appointment_time")

        if not appt_date or not appt_time:
            return cleaned

        self.validate_slot_collision(cleaned)
        return cleaned

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Your Name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Your Email"}),
    )
    subject = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Subject"}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 7, "placeholder": "Message"}),
    )
