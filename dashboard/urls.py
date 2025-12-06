from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import RememberMeLoginView

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='home'),
    path('appointments/', views.appointments, name='appointments'),
    path('appointments/new/', views.appointment_form, name='appointment_form'),
    path('patients/', views.patients, name='patients'),
    path('message/', views.message, name='message'),
    path('profile/', views.profile, name='profile'),
    path('blog/', views.blog, name='blog'),
    path('login/',  RememberMeLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('chart-date/', views.appointments_chart, name='appointments_chart'),
]
