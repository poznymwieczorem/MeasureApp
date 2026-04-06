from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
import plotly.express as px
import pandas as pd

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

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    electrodes = Electrode.objects.filter(biomarker__project=project).prefetch_related('measurements')
    return render(request, 'measurements/project_detail.html', {
        'project': project,
        'electrodes': electrodes,
    })

@login_required
def calendar_data(request):
    
    measurements = Measurement.objects.filter(
        electrode__biomarker__project__members=request.user
    ).select_related('electrode')
    
    events = []
    for m in measurements:
        events.append({
            'title': f"{m.technique} - {m.electrode.label}",
            'start': m.date_performed.isoformat(),
            'url': reverse('measurement_detail', args=[m.id]),
            'color': '#0d6efd' if m.technique == 'CV' else '#198754' # Różne kolory dla technik!
        })
    return JsonResponse(events, safe=False)

@login_required
def measurement_detail(request, pk):
    measurement = get_object_or_404(Measurement, pk=pk)
    plot_div = None

    if measurement.csv_file:
        try:
            df = pd.read_csv(measurement.csv_file.path)
            
            fig = px.line(
                df, x='Vf', y='Im',
                title=f"Wolamperogram {measurement.electrode.label} ({measurement.technique})",
                labels={'Vf': 'Napięcie (V)', 'Im': 'Prąd (A)'},
                template='plotly_white'
            )

            if measurement.peak_potelntial and measurement.peak_current:
                fig.add_scatter(
                    x=[measurement.peak_potelntial], 
                    y=[measurement.peak_current], 
                    mode='markers',
                    name='Wykryty PIK',
                    marker=dict(color='red', size=12, symbol='x')
                )
            
            fig.update_layout(autosize=True)
            plot_div = fig.to_html(full_html=False, config={'displayModeBar': True})

        except Exception as e:
            print(f"Error generating plot: {e}")

    return render(request, 'measurements/measurement_detail.html', {
        'measurement': measurement,
        'plot_div': plot_div
    })