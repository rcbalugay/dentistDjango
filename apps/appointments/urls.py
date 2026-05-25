from django.urls import path
from . import views

urlpatterns = [
    path("appointment/", views.appointment_form, name="appointment_form"),
    path("appointment/status/", views.appointment_status, name="appointment_status"),
    path("appointment/check/", views.check_appointment_slot, name="check_appointment_slot"),
]
