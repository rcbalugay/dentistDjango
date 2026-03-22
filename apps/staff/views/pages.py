from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .auth import staff_only

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def message(request):
	return render(request, 'staff/pages/message.html', {
        "active_page": "message",
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def blog(request):
	return render(request, 'staff/pages/blog.html', {
        "active_page": "blog",
    })

@login_required(login_url="dashboard:login")
@user_passes_test(staff_only)
def profile(request):
	return render(request, 'staff/pages/profile.html', {
        "active_page": "profile",
    })