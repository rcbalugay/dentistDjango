from django.urls import path
from . import views

urlpatterns = [
	path('', views.home, name='home'),
	path('contact/', views.contact, name='contact'),
	path('about/', views.about, name='about'),
	path('blog/', views.blog, name='blog'),
	path('services/', views.services, name='services'),
	path('doctor/', views.doctor, name="doctor"),
	path('appointment/', views.appointment_form, name="appointment_form"),
]