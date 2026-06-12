from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Measurement, Biomarker, Electrode, Project
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile


class ElectrodeModelsTest(TestCase):
    """Testy modeli i relacji M2M między Project, Biomarker, Electrode."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.project = Project.objects.create(name='Test Project', description='A test project')
        self.project.members.add(self.user)

        self.biomarker = Biomarker.objects.create(name='Glukoza')
        self.biomarker.projects.add(self.project)

        self.electrode = Electrode.objects.create(label='E1', material='Gold')
        self.electrode.projects.add(self.project)

    def test_biomarker_m2m_project(self):
        """Biomarker jest powiązany z projektem przez M2M."""
        self.assertIn(self.project, self.biomarker.projects.all())
        self.assertIn(self.biomarker, self.project.biomarkers.all())

    def test_electrode_m2m_project(self):
        """Elektroda jest powiązana z projektem przez M2M."""
        self.assertIn(self.project, self.electrode.projects.all())
        self.assertIn(self.electrode, self.project.electrodes.all())

    def test_shared_electrode_between_projects(self):
        """Jedna elektroda może być współdzielona między projektami."""
        project2 = Project.objects.create(name='Projekt 2')
        self.electrode.projects.add(project2)
        self.assertEqual(self.electrode.projects.count(), 2)

    def test_measurement_creation(self):
        """Pomiar jest powiązany z projektem, elektrodą i biomarkerem."""
        m = Measurement.objects.create(
            electrode=self.electrode,
            biomarker=self.biomarker,
            project=self.project,
            technique='CV',
            date_performed=timezone.now(),
        )
        self.assertEqual(self.electrode.measurements.count(), 1)
        self.assertEqual(m.electrode.label, 'E1')
        self.assertEqual(m.project, self.project)
        self.assertEqual(m.biomarker.name, 'Glukoza')


class AccessAndAuthenticationTest(TestCase):
    """Testy autoryzacji i dostępu do chronionych widoków."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_login_process(self):
        login = self.client.login(username='testuser', password='password123')
        self.assertTrue(login)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Witaj w Laboratorium')

    def test_logout_process(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)

        dash_response = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_response.status_code, 302)

    def test_root_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/login/')


class ParserTest(TestCase):
    """Testy parsera plików .DTA — ścieżka sukcesu i odporność na błędne dane."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.biomarker = Biomarker.objects.create(name="Glucose")
        self.biomarker.projects.add(self.project)
        self.electrode = Electrode.objects.create(label="E1", material="Gold")
        self.electrode.projects.add(self.project)

    def test_dta_parsing_logic(self):
        """Parser poprawnie parsuje plik .DTA, tworzy CSV i wyznacza pik."""
        dta_content = (
            "TAG\tSomething\n"
            "BAH\tSomething else\n"
            "CURVE\tTABLE\n"
            "Pt\tT\tVf\tIm\tVu\tSig\tAch\tIERange\tOver\tTemp\n"
            "#\ts\tV vs. Ref.\tA\tV\tV\tV\t#\tbits\tdeg C\n"
            "0\t0.02\t4.99611E-001\t5.23368E-005\t0.00000E+000\t4.99991E-001\t0.00000E+000\t10\t...........\t1464.99\n"
            "1\t0.04\t4.98582E-001\t5.27342E-005\t0.00000E+000\t4.98991E-001\t0.00000E+000\t9\t...........\t1464.99\n"
            "2\t0.06\t4.97582E-001\t6.65984E-005\t0.00000E+000\t4.97992E-001\t0.00000E+000\t8\t...........\t1464.99\n"
            "3\t0.08\t4.96609E-001\t5.20958E-005\t0.00000E+000\t4.96992E-001\t0.00000E+000\t8\t...........\t1464.99\n"
            "4\t0.1\t4.95586E-001\t7.84788E-005\t0.00000E+000\t4.95992E-001\t0.00000E+000\t8\t...........\t1464.99\n"
        ).encode('utf-8')

        test_file = SimpleUploadedFile("test_data.DTA", dta_content)

        measurement = Measurement.objects.create(
            electrode=self.electrode,
            biomarker=self.biomarker,
            project=self.project,
            technique='CV',
            date_performed=timezone.now(),
            raw_file=test_file,
        )
        measurement.refresh_from_db()

        self.assertTrue(measurement.csv_file)
        self.assertTrue(measurement.csv_file.name.endswith('.csv'))
        self.assertIsNotNone(measurement.peak_potelntial)
        self.assertIsNotNone(measurement.peak_current)

    def test_invalid_file_handling(self):
        """Parser nie crashuje na uszkodzonym pliku — brak CSV i piku, bez błędu 500."""
        bad_file = SimpleUploadedFile("garbage.DTA", b"This is not a valid .dta file content")

        measurement = Measurement.objects.create(
            electrode=self.electrode,
            project=self.project,
            technique='CV',
            date_performed=timezone.now(),
            raw_file=bad_file,
        )
        measurement.refresh_from_db()

        self.assertFalse(measurement.csv_file)
        self.assertIsNone(measurement.peak_potelntial)
        self.assertIsNone(measurement.peak_current)


class CreateStructureTest(TestCase):
    """Testy dynamicznego formularza tworzenia projektu z biomarkerami i elektrodami."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="1234")
        self.client.login(username="testuser", password="1234")

    def test_create_project_with_new_biomarker_and_electrode(self):
        """Tworzenie projektu z nowymi biomarkerami i elektrodami."""
        response = self.client.post(
            reverse("create_structure"),
            {
                "project-name": "Projekt X",
                "project-description": "Opis testowy",
                "biomarker_names[]": ["Glukoza", "CRP"],
                "electrode_labels[]": ["E1", "E2"],
                "electrode_materials[]": ["Au", "Graphene"],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Project.objects.count(), 1)

        project = Project.objects.first()
        self.assertEqual(project.name, "Projekt X")
        self.assertIn(self.user, project.members.all())
        self.assertEqual(project.biomarkers.count(), 2)
        self.assertEqual(project.electrodes.count(), 2)

    def test_create_project_with_existing_biomarker(self):
        """Istniejący biomarker można przypisać do nowego projektu przez checkbox."""
        existing = Biomarker.objects.create(name="Dopamina")

        response = self.client.post(
            reverse("create_structure"),
            {
                "project-name": "Projekt Y",
                "project-description": "",
                "existing_biomarker_ids[]": [str(existing.id)],
                "electrode_labels[]": ["E1"],
                "electrode_materials[]": [""],
            },
        )

        self.assertEqual(response.status_code, 302)
        project = Project.objects.first()
        self.assertIn(existing, project.biomarkers.all())

    def test_invalid_form(self):
        """Brak nazwy projektu — nic nie powstaje."""
        response = self.client.post(
            reverse("create_structure"),
            {"project-name": ""},
        )
        self.assertEqual(Project.objects.count(), 0)

    def test_requires_login(self):
        """Niezalogowany użytkownik jest przekierowany do loginu."""
        self.client.logout()
        response = self.client.post(reverse("create_structure"))
        self.assertEqual(response.status_code, 302)


class ProjectDetailTest(TestCase):
    """Testy widoku projektu: dodawanie/usuwanie elektrod i biomarkerów, filtrowanie, eksport."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.client.login(username='testuser', password='test123')

        self.project = Project.objects.create(name='Projekt Testowy', description='Opis')
        self.project.members.add(self.user)

        self.biomarker = Biomarker.objects.create(name='CRP')
        self.biomarker.projects.add(self.project)

        self.electrode = Electrode.objects.create(label='E1', material='Au')
        self.electrode.projects.add(self.project)

    def test_project_detail_page_loads(self):
        response = self.client.get(reverse('project_detail', args=[self.project.id]))
        self.assertEqual(response.status_code, 200)

    def test_project_edit_updates_data(self):
        url = reverse('project_edit', args=[self.project.id])
        response = self.client.post(url, {'name': 'Nowa nazwa', 'description': 'Nowy opis'})
        self.assertRedirects(response, reverse('project_detail', args=[self.project.id]))
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Nowa nazwa')

    def test_add_new_electrode_to_project(self):
        """Dodanie nowej elektrody do istniejącego projektu."""
        url = reverse('add_electrode_to_project', args=[self.project.id])
        response = self.client.post(url, {'label': 'E2', 'material': 'Pt'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.electrodes.count(), 2)

    def test_add_existing_electrode_to_project(self):
        """Przypisanie istniejącej elektrody do projektu."""
        other = Electrode.objects.create(label='E3', material='Ag')
        url = reverse('add_electrode_to_project', args=[self.project.id])
        response = self.client.post(url, {'existing_electrode': str(other.id)})
        self.assertEqual(response.status_code, 302)
        self.assertIn(other, self.project.electrodes.all())

    def test_remove_electrode_from_project(self):
        """Usunięcie elektrody z projektu (M2M — obiekt zostaje w bazie)."""
        url = reverse('remove_electrode_from_project', args=[self.project.id, self.electrode.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.electrodes.count(), 0)
        self.assertTrue(Electrode.objects.filter(pk=self.electrode.id).exists())

    def test_remove_biomarker_from_project(self):
        """Usunięcie biomarkera z projektu (M2M — obiekt zostaje w bazie)."""
        url = reverse('remove_biomarker_from_project', args=[self.project.id, self.biomarker.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.project.biomarkers.count(), 0)
        self.assertTrue(Biomarker.objects.filter(pk=self.biomarker.id).exists())

    def test_export_csv(self):
        """Eksport CSV zawiera nagłówki i zwraca poprawny content type."""
        Measurement.objects.create(
            electrode=self.electrode,
            biomarker=self.biomarker,
            project=self.project,
            technique='DPV',
            date_performed=timezone.now(),
        )
        url = reverse('export_project_csv', args=[self.project.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode('utf-8-sig')
        self.assertIn('Elektroda', content)
        self.assertIn('E1', content)

    def test_search_filter_by_electrode(self):
        """Filtrowanie pomiarów po elektrodzie zwraca tylko pasujące wyniki."""
        Measurement.objects.create(
            electrode=self.electrode,
            project=self.project,
            technique='CV',
            date_performed=timezone.now(),
        )
        url = reverse('project_detail', args=[self.project.id])
        response = self.client.get(url, {'electrode': self.electrode.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_pagination(self):
        """Stronicowanie — 15 pomiarów przy 10/stronę daje 2 strony."""
        for i in range(15):
            Measurement.objects.create(
                electrode=self.electrode,
                project=self.project,
                technique='CV',
                date_performed=timezone.now(),
            )
        url = reverse('project_detail', args=[self.project.id])
        response = self.client.get(url)
        self.assertEqual(len(response.context['page_obj']), 10)

        response2 = self.client.get(url, {'page': 2})
        self.assertEqual(len(response2.context['page_obj']), 5)
