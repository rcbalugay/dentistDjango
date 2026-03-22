from django.urls import path
from . import views

urlpatterns = [
    path("appointment/", views.appointment_form, name="appointment_form"),
    path("appointment/status/", views.appointment_status, name="appointment_status"),
]
