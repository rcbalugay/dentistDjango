from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    RememberMeLoginView,
    appointments,
    appointments_chart,
    appointments_form,
    blog,
    index,
    message,
    patients,
    profile,
)

app_name = "dashboard"

urlpatterns = [
    path("", index, name="home"),
    path("appointments/", appointments, name="appointments"),
    path("appointments/new/", appointments_form, name="appointments_form"),
    path("patients/", patients, name="patients"),
    path("message/", message, name="message"),
    path("profile/", profile, name="profile"),
    path("blog/", blog, name="blog"),
    path("login/", RememberMeLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("chart-date/", appointments_chart, name="appointments_chart"),
]
