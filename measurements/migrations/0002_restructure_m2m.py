"""
Migracja 2: Przebudowa struktury bazy danych z zachowaniem danych.

Kolejność operacji:
1. Dodaj nowe pola (M2M, FK) jako nullable
2. Skopiuj dane ze starych relacji do nowych (RunPython)
3. Usuń stare pola
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_data_forward(apps, schema_editor):
    """
    Przepisuje dane ze starej struktury do nowej:
    - Biomarker.project (FK) -> Biomarker.projects (M2M)
    - Electrode.biomarker (FK) -> Electrode.projects (M2M) na podstawie biomarkera
    - Measurement.electrode -> Measurement.project przez łańcuch electrode->biomarker->project
    - Measurement.electrode -> Measurement.biomarker przez electrode.biomarker
    - Measurement.date_performed (date string) -> date_performed (datetime)
    """
    Biomarker = apps.get_model('measurements', 'Biomarker')
    Electrode = apps.get_model('measurements', 'Electrode')
    Measurement = apps.get_model('measurements', 'Measurement')

    # 1. Biomarker.project (FK) -> Biomarker.projects (M2M)
    for biomarker in Biomarker.objects.select_related('project').all():
        if biomarker.project_id:
            biomarker.projects.add(biomarker.project_id)

    # 2. Electrode.biomarker (FK) -> Electrode.projects (M2M)
    #    Elektroda dziedziczy projekt po swoim biomarkerze
    for electrode in Electrode.objects.select_related('biomarker__project').all():
        if electrode.biomarker_id and electrode.biomarker.project_id:
            electrode.projects.add(electrode.biomarker.project_id)

    # 3. Measurement -> przypisz project i biomarker
    for m in Measurement.objects.select_related(
        'electrode__biomarker__project'
    ).all():
        electrode = m.electrode
        if electrode and electrode.biomarker_id:
            biomarker = electrode.biomarker
            m.biomarker = biomarker
            if biomarker.project_id:
                m.project_id = biomarker.project_id
            m.save(update_fields=['biomarker', 'project'])


def migrate_data_backward(apps, schema_editor):
    """
    Cofa migrację: przywraca stare FK z M2M (bierze pierwszy element).
    """
    Biomarker = apps.get_model('measurements', 'Biomarker')
    Electrode = apps.get_model('measurements', 'Electrode')

    for biomarker in Biomarker.objects.prefetch_related('projects').all():
        first_project = biomarker.projects.first()
        if first_project:
            biomarker.project = first_project
            biomarker.save(update_fields=['project'])

    for electrode in Electrode.objects.prefetch_related('projects').all():
        # Przywróć powiązanie z biomarkerem przez projekt (heurystyka: pierwszy biomarker projektu)
        pass  # trudno odwrócić bez ambiguity — electrode.biomarker zostaje NULL


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0001_initial'),
    ]

    operations = [
        # ── KROK 1: Dodaj nowe pola (nullable, żeby nie blokować istniejących wierszy) ──

        # Nowy FK: Measurement.project
        migrations.AddField(
            model_name='measurement',
            name='project',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='measurements',
                to='measurements.project',
            ),
        ),

        # Nowy FK: Measurement.biomarker
        migrations.AddField(
            model_name='measurement',
            name='biomarker',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='measurements',
                to='measurements.biomarker',
            ),
        ),

        # Zmień date_performed: DateField -> DateTimeField (zachowuje istniejące daty, ustawia czas 00:00)
        migrations.AlterField(
            model_name='measurement',
            name='date_performed',
            field=models.DateTimeField(
                verbose_name='Measurement Date & Time',
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),

        # M2M: Biomarker <-> Project
        migrations.AddField(
            model_name='biomarker',
            name='projects',
            field=models.ManyToManyField(
                blank=True,
                related_name='biomarkers',
                to='measurements.project',
            ),
        ),

        # M2M: Electrode <-> Project
        migrations.AddField(
            model_name='electrode',
            name='projects',
            field=models.ManyToManyField(
                blank=True,
                related_name='electrodes',
                to='measurements.project',
            ),
        ),

        # ── KROK 2: Przepisz dane ze starych pól do nowych ──
        migrations.RunPython(
            migrate_data_forward,
            reverse_code=migrate_data_backward,
        ),

        # ── KROK 3: Usuń stare pola (dopiero po przepisaniu danych) ──
        migrations.RemoveField(
            model_name='biomarker',
            name='project',
        ),
        migrations.RemoveField(
            model_name='electrode',
            name='biomarker',
        ),
    ]
