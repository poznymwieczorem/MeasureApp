from django.contrib import admin

# Register your models here.

from .models import Project, Biomarker, Electrode, Measurement

admin.site.register(Project)
admin.site.register(Biomarker)
admin.site.register(Electrode)
admin.site.register(Measurement)