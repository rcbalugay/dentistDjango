from django import forms
from .models import Appointment, Patient
from .constants import APPOINTMENT_SERVICES

class AppointmentForm(forms.ModelForm):
    """
    Shared form for booking appointments.
    Used by:
      - Landing page (status = PENDING)
      - Dashboard manual booking (status = CONFIRMED)
    """
    
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
    
    def clean(self):
      cleaned = super().clean()
      appt_date = cleaned.get("appointment_date")
      appt_time = cleaned.get("appointment_time")

      # Check if either is missing; let normal "required" errors handle it
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
          # This shows as a "non-field" error at the top of the form
          raise forms.ValidationError(
            "The selected date or time is already booked. Please choose a different date or time."
          )

      # Additional validation can be added here if needed
      return cleaned

    def save(self, commit=True, status=None):
        """
        Save the Appointment instance, converting appointment_date + appointment_time
        into the model fields date + timeslot, and saving services as a list.
        Optional 'status' lets caller decide PENDING vs CONFIRMED.
        """
        instance = super().save(commit=False)

        date_obj = self.cleaned_data["appointment_date"]
        time_obj = self.cleaned_data["appointment_time"]

        timeslot_str = self.cleaned_data.get("timeslot_str") or \
                       time_obj.strftime("%I:%M %p").lstrip("0")
        
        instance.date = date_obj
        instance.start_time = time_obj
        instance.timeslot = timeslot_str
        services = self.cleaned_data.get("services") or []
        services = sorted({s.strip() for s in services if s.strip()})
        instance.services = services

        # GET Patient details
        name = self.cleaned_data.get("name", "").strip()
        phone = self.cleaned_data.get("phone", "").strip()
        email = self.cleaned_data.get("email", "").strip()

        patient = None
        
        if phone:
          patient = Patient.objects.filter(phone=phone).first()

        if not patient and email:
          patient = Patient.objects.filter(email=email).first()

        if not patient and name:
          # fallback: find same name only if no identifiers
          patient = Patient.objects.filter(name__iexact=name, phone=phone, email=email)

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