import csv

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator
import plotly.express as px
import pandas as pd

from .models import Project, Measurement, Electrode, Biomarker

from django.contrib import messages
from .forms import (
    RegisterForm, ProjectForm, BiomarkerForm, ElectrodeForm,
    MeasurementForm, MeasurementSearchForm,
)
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.core import settings


@login_required
def dashboard(request):
    user_projects = Project.objects.filter(members=request.user)

    total_m = Measurement.objects.filter(project__in=user_projects).count()
    week_ago = timezone.now() - timedelta(days=7)
    recent_m = Measurement.objects.filter(
        project__in=user_projects, created_at__gte=week_ago
    ).count()

    project_form = ProjectForm(prefix="project")
    biomarker_form = BiomarkerForm(prefix="biomarker")
    electrode_form = ElectrodeForm(prefix="electrode")

    context = {
        'projects': user_projects,
        'total_measurements': total_m,
        'recent_count': recent_m,
        'project_form': project_form,
        'biomarker_form': biomarker_form,
        'electrode_form': electrode_form,
        'measurement_choices': Measurement.TECHNIQUES,
        'all_electrodes': Electrode.objects.all(),
        'all_biomarkers': Biomarker.objects.all(),

    }
    return render(request, 'measurements/dashboard.html', context)


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    search_form = MeasurementSearchForm(request.GET or None, project=project)

    measurements_qs = Measurement.objects.filter(project=project).select_related(
        'electrode', 'biomarker'
    )

    if search_form.is_valid():
        if search_form.cleaned_data.get('date_from'):
            measurements_qs = measurements_qs.filter(
                date_performed__date__gte=search_form.cleaned_data['date_from']
            )
        if search_form.cleaned_data.get('date_to'):
            measurements_qs = measurements_qs.filter(
                date_performed__date__lte=search_form.cleaned_data['date_to']
            )
        if search_form.cleaned_data.get('electrode'):
            measurements_qs = measurements_qs.filter(
                electrode=search_form.cleaned_data['electrode']
            )
        if search_form.cleaned_data.get('biomarker'):
            measurements_qs = measurements_qs.filter(
                biomarker=search_form.cleaned_data['biomarker']
            )

    # Zmiana 5: Stronicowanie — 10 pomiarów na stronę
    paginator = Paginator(measurements_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    biomarker_form = BiomarkerForm()
    electrode_form = ElectrodeForm()

    all_electrodes = Electrode.objects.exclude(pk__in=project.electrodes.all())
    all_biomarkers = Biomarker.objects.exclude(pk__in=project.biomarkers.all())

    return render(request, 'measurements/project_detail.html', {
        'project': project,
        'electrodes': project.electrodes.all(),
        'biomarkers': project.biomarkers.all(),
        'all_electrodes': all_electrodes,
        'all_biomarkers': all_biomarkers,
        'page_obj': page_obj,
        'measurement_choices': Measurement.TECHNIQUES,
        'search_form': search_form,
        'biomarker_form': biomarker_form,
        'electrode_form': electrode_form,
    })

@login_required
def remove_electrode_from_project(request, pk, electrode_id):
    project = get_object_or_404(Project, pk=pk)
    electrode = get_object_or_404(Electrode, pk=electrode_id)
    if request.method == 'POST':
        electrode.projects.remove(project)
    return redirect('project_detail', pk=pk)


@login_required
def remove_biomarker_from_project(request, pk, biomarker_id):
    project = get_object_or_404(Project, pk=pk)
    biomarker = get_object_or_404(Biomarker, pk=biomarker_id)
    if request.method == 'POST':
        biomarker.projects.remove(project)
    return redirect('project_detail', pk=pk)

@login_required
def add_electrode_to_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        existing_id = request.POST.get('existing_electrode')
        if existing_id:
            electrode = get_object_or_404(Electrode, pk=existing_id)
            electrode.projects.add(project)
        else:
            form = ElectrodeForm(request.POST)
            if form.is_valid():
                electrode = form.save()
                electrode.projects.add(project)
    return redirect('project_detail', pk=pk)


@login_required
def add_biomarker_to_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        existing_id = request.POST.get('existing_biomarker')
        if existing_id:
            biomarker = get_object_or_404(Biomarker, pk=existing_id)
            biomarker.projects.add(project)
        else:
            form = BiomarkerForm(request.POST)
            if form.is_valid():
                biomarker = form.save()
                biomarker.projects.add(project)
    return redirect('project_detail', pk=pk)

@login_required
def export_project_csv(request, pk):
    """Zmiana 3: Eksport pomiarów projektu do CSV."""
    project = get_object_or_404(Project, pk=pk)
    measurements = Measurement.objects.filter(project=project).select_related(
        'electrode', 'biomarker'
    )

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="{project.name}_measurements.csv"'
    )
    response.write('\ufeff')  # BOM dla Excela

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Elektroda', 'Biomarker', 'Technika',
        'Data i godzina pomiaru', 'Pik potencjału (V)', 'Pik prądu (A)',
        'LOD', 'LOQ',
    ])
    for m in measurements:
        writer.writerow([
            m.id,
            m.electrode.label,
            m.biomarker.name if m.biomarker else '',
            m.get_technique_display(),
            m.date_performed.strftime('%Y-%m-%d %H:%M'),
            m.peak_potelntial if m.peak_potelntial is not None else '',
            m.peak_current if m.peak_current is not None else '',
            m.lod if m.lod is not None else '',
            m.loq if m.loq is not None else '',
        ])
    return response


@login_required
def calendar_data(request):
    measurements = Measurement.objects.filter(
        project__members=request.user
    ).select_related('electrode')

    events = []
    for m in measurements:
        events.append({
            'title': f"{m.technique} - {m.electrode.label}",
            'start': m.date_performed.isoformat(),
            'url': reverse('measurement_detail', args=[m.id]),
            'color': '#0d6efd' if m.technique == 'CV' else '#198754',
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
                template='plotly_white',
            )
            if measurement.peak_potelntial and measurement.peak_current:
                fig.add_scatter(
                    x=[measurement.peak_potelntial],
                    y=[measurement.peak_current],
                    mode='markers',
                    name='Wykryty PIK',
                    marker=dict(color='red', size=12, symbol='x'),
                )
            fig.update_layout(autosize=True)
            plot_div = fig.to_html(full_html=False, config={'displayModeBar': True})
        except Exception as e:
            print(f"Error generating plot: {e}")

    return render(request, 'measurements/measurement_detail.html', {
        'measurement': measurement,
        'plot_div': plot_div,
    })

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            if settings.REQUIRE_EMAIL_VERIFICATION:
                # Wersja lokalna: konto nieaktywne, link aktywacyjny mailem
                user.is_active = False
                user.save()

                current_site = get_current_site(request)
                mail_subject = 'Aktywuj swoje konto w MeasureLapp'
                message = render_to_string('registration/acc_active_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                })
                to_email = form.cleaned_data.get('email')
                email = EmailMessage(mail_subject, message, to=[to_email])
                email.send()
                return render(request, 'registration/check_email.html')
            else:
                # Wersja produkcyjna (Render, brak SMTP): konto od razu aktywne
                user.is_active = True
                user.save()
                messages.success(request, 'Konto utworzone! Możesz się zalogować.')
                return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Twoje konto zostało aktywowane! Możesz się zalogować.')
        return redirect('login')
    else:
        return render(request, 'registration/activation_invalid.html')


@login_required
def create_structure(request):
    if request.method == "POST":
        project_form = ProjectForm(request.POST, prefix="project")

        if project_form.is_valid():
            project = project_form.save()
            project.members.add(request.user)

            # Istniejące biomarkery (checkboxy)
            existing_biomarker_ids = request.POST.getlist('existing_biomarker_ids[]')
            for bid in existing_biomarker_ids:
                try:
                    biomarker = Biomarker.objects.get(pk=bid)
                    biomarker.projects.add(project)
                except Biomarker.DoesNotExist:
                    pass

            # Nowe biomarkery
            biomarker_names = request.POST.getlist('biomarker_names[]')
            for name in biomarker_names:
                name = name.strip()
                if name:
                    biomarker = Biomarker.objects.create(name=name)
                    biomarker.projects.add(project)

            # Istniejące elektrody (checkboxy)
            existing_electrode_ids = request.POST.getlist('existing_electrode_ids[]')
            for eid in existing_electrode_ids:
                try:
                    electrode = Electrode.objects.get(pk=eid)
                    electrode.projects.add(project)
                except Electrode.DoesNotExist:
                    pass

            # Nowe elektrody
            electrode_labels = request.POST.getlist('electrode_labels[]')
            electrode_materials = request.POST.getlist('electrode_materials[]')
            for i, label in enumerate(electrode_labels):
                label = label.strip()
                if label:
                    material = electrode_materials[i].strip() if i < len(electrode_materials) else ''
                    electrode = Electrode.objects.create(label=label, material=material)
                    electrode.projects.add(project)

    return redirect("dashboard")


def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'measurements/project_edit.html', {
        'form': form,
        'project': project,
    })


@login_required
def measurement_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        electrode_id = request.POST.get('electrode')
        biomarker_id = request.POST.get('biomarker') or None
        technique = request.POST.get('technique')
        date_performed = request.POST.get('date_performed')  # datetime-local format
        raw_file = request.FILES.get('raw_file')

        electrode = get_object_or_404(Electrode, pk=electrode_id)

        # Zabezpieczenie: elektroda musi należeć do projektu
        if not electrode.projects.filter(pk=project.pk).exists():
            return redirect('project_detail', pk=project.id)

        biomarker = None
        if biomarker_id:
            biomarker = get_object_or_404(Biomarker, pk=biomarker_id)

        Measurement.objects.create(
            electrode=electrode,
            biomarker=biomarker,
            project=project,
            technique=technique,
            date_performed=date_performed,
            raw_file=raw_file,
        )

    return redirect('project_detail', pk=project.id)
