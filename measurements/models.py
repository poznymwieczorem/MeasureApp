from django.db import models
from django.contrib.auth.models import User
import os

from .utils import process_dta_file

class Project(models.Model):
    name = models.CharField("Project Name", max_length=200)
    description = models.TextField("Project Description", blank=True)
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    # Optional: Add a user field to associate projects with users
    members = models.ManyToManyField(User, related_name='projects')

    def __str__(self):
        return self.name

class Biomarker (models.Model):
    name = models.CharField("Biomarker Name", max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='biomarkers')
    
    def __str__ (self):
        return F"{self.name} ({self.project.name})"
    
class Electrode(models.Model):
    label = models.CharField("Electrode Label", max_length=100)
    material = models.CharField("Electrode Material", max_length=100, blank=True)
    biomarker = models.ForeignKey(Biomarker, on_delete=models.CASCADE, related_name='electrodes')

    def __str__ (self):
        return self.label
    
class Measurement(models.Model):
    TECHNIQUES = [
        ('EIS', 'Electrochemical Impedance Spectroscopy'),
        ('CV', 'Cyclic Voltammetry'),
        ('DPV', 'Differential Pulse Voltammetry'),
        ('SWV', 'Square Wave Voltammetry'),
        ('CA', 'Chronoamperometry'),
        ('HER', 'Hydrogen Evolution Reaction'),
        ('OER', 'Oxygen Evolution Reaction'),
        ('ORR', 'Oxygen Reduction Reaction'),
        ('Other', 'Other'),
    ]

    electrode = models.ForeignKey(Electrode, on_delete=models.CASCADE, related_name='measurements')
    technique = models.CharField(max_length=5, choices=TECHNIQUES)
    date_performed = models.DateField("Measurement Date")
    created_at = models.DateTimeField(auto_now_add=True)

    # File
    raw_file = models.FileField("Raw Data .DTA", upload_to= "uploads/raw/%Y/%m/")
    csv_file = models.FileField("Processed Data .CSV", upload_to= "uploads/csv/%Y/%m/", blank=True, null=True)

    # Results (automatic fields to be filled after processing the raw data)
    peak_potelntial = models.FloatField("Peak Potential (V)", blank=True, null=True)
    peak_current = models.FloatField("Peak Current (A)", blank=True, null=True)

    lod = models.FloatField("Limit of Detection (LOD)", blank=True, null=True)
    loq = models.FloatField("Limit of Quantification (LOQ)", blank=True, null=True)

    class Meta:
        ordering = ['-date_performed']
    
    def __str__(self):
        return f"{self.technique} on {self.electrode.label} ({self.date_performed})"
    
    def save(self, *args, **kwargs):

        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and self.raw_file:
            process_dta_file(self)
            super().save(update_fields=['csv_file', 'peak_potelntial', 'peak_current'])