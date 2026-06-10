from django.contrib import admin
from .models import Project, Biomarker, Electrode, Measurement


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    filter_horizontal = ['members']


@admin.register(Biomarker)
class BiomarkerAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ['projects']


@admin.register(Electrode)
class ElectrodeAdmin(admin.ModelAdmin):
    list_display = ['label', 'material']
    filter_horizontal = ['projects']


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['technique', 'electrode', 'biomarker', 'project', 'date_performed']
    list_filter = ['technique', 'project', 'electrode', 'biomarker']
    search_fields = ['electrode__label', 'biomarker__name', 'project__name']
    date_hierarchy = 'date_performed'
