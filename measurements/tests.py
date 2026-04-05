from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Measurement, Biomarker, Electrode, Project
from datetime import date

class ElectrodeModelsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.project = Project.objects.create(name='Test Project', description='A test project')
        self.project.members.add(self.user)
        self.biomarker = Biomarker.objects.create(name='Glukoza', project=self.project)
        self.electrode = Electrode.objects.create(label='E1', material='Gold', biomarker=self.biomarker)

    def test_hierarchy_integration(self):
        self.assertEqual(self.electrode.biomarker.name, 'Glukoza')
        self.assertEqual(self.electrode.biomarker.project.name, 'Test Project')

    def test_measurement_creation(self):
        m = Measurement.objects.create(
            electrode = self.electrode,
            technique = 'CV',
            date_performed = date.today(),
            peak_potelntial = None,
            peak_current = None,
            lod = None,
            loq = None
        )
        self.assertEqual(self.electrode.measurements.count(), 1)
        self.assertEqual(m.electrode.label, 'E1')

class AccessAndAuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

        def test_dashboard_requires_login(self):
            response = self.client.get(reverse('dashboard'))
            self.assertEqual(response.status_code, 302)  # Redirect to login
            self.assertIn('/login/', response.url)

        def test_login_process(self):
            login = self.client.login(username='testuser', password='password123')
            self.assertTrue(login)
            response = self.client.get(reverse('dashboard'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Dashboard')  # Assuming the dashboard template contains this text

# Create your tests here.
