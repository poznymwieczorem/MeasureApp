from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone

from .models import Project, Measurement, Electrode

@login_required
def dashboard(request):
    user_projects = Project.objects.filter(members=request.user)

    total_m = Measurement.objects.filter(electrode__biomarker__project__in=user_projects).count()
    week_ago = timezone.now() - timedelta(days=7)
    recent_m = Measurement.objects.filter(created_at__gte=week_ago).count()

    all_electrodes = Electrode.objects.filter(biomarker__project__in=user_projects)

    context = {
        'projects': user_projects,
        'total_measurements': total_m,
        'recent_count': recent_m,
        'all_electrodes': all_electrodes,
    }
    return render(request, 'measurements/dashboard.html', context)

