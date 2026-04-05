from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from .models import Measurement

@login_required
def dashboard(request):
    recent_measurements = Measurement.objects.all()[:10]
    return render(request, 'measurements/dashboard.html', {'measurements': recent_measurements})

