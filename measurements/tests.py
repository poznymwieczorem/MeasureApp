from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Measurement, Biomarker, Electrode, Project
from datetime import date
import io
from django.core.files.uploadedfile import SimpleUploadedFile

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
            self.assertContains(response, '<h2 class="fw-bold">Witaj w Laboratorium</h2>')  # Assuming the dashboard template contains this text

    def test_logout_process(self):
            login = self.client.login(username = 'testuser', password = 'password123')
            response = self.client.post(reverse('logout'))
            self.assertEqual(response.status_code, 302)  # Redirect after logout

            dash_response = self.client.get(reverse('dashboard'))
            self.assertEqual(dash_response.status_code, 302)  # Should redirect to login again

    def test_root_redirects_to_login(self):
            response = self.client.get('/')
            self.assertRedirects(response, '/login/')

class ParserTest(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project", description="A test project")
        self.biomarker = Biomarker.objects.create(name="Glucose", project = self.project)
        self.electrode = Electrode.objects.create(label="E1", material="Gold", biomarker=self.biomarker)

    def test_dta_parsing_logic(self):
        """
        Test the parsing logic with a sample .dta content.
        """

        # Create a sample .dta file content
        dta_content = (
            "TAG\tSomething\n"
            "BAH\tSomething else\n"
            "CURVE\tTABLE\n"
            "Pt\tT\tVf\tIm\tVu\tSig\tAch\tIERange\tOver\tTemp\n"
	        "#\ts\tV vs. Ref.\tA\tV\tV\tV\t#\tbits\tdeg C\n"
	        "0\t0.02\t4.99611E-001\t5.23368E-005\t0.00000E+000\t4.99991E-001\t0.00000E+000\t10\t...........\t1464.99\n"
	        "1\t0.04\t4.98582E-001\t5.27342E-005\t0.00000E+000\t4.98991E-001\t0.00000E+000\t9\t...........\t1464.99\n"
	        "2\t0.06\t4.97582E-001\t6.65984E-005\t0.00000E+000\t4.97992E-001\t0.00000E+000\t8\t...........\t1464.99\n" # This is the highest peak
	        "3\t0.08\t4.96609E-001\t5.20958E-005\t0.00000E+000\t4.96992E-001\t0.00000E+000\t8\t...........\t1464.99\n"
	        "4\t0.1\t4.95586E-001\t7.84788E-005\t0.00000E+000\t4.95992E-001\t0.00000E+000\t8\t...........\t1464.99\n"
        ).encode('utf-8')
        
        test_file = SimpleUploadedFile("test_data.DTA", dta_content)

        # Create a Measurement instance with the test file
        measurement = Measurement.objects.create(
            electrode = self.electrode,
            technique = 'CV',
            date_performed = date.today(),
            raw_file = test_file
        )

        # Refresh from DB to get updated fields
        measurement.refresh_from_db()

        # ...::: Assertions ::...

        # Check if CSV file was created
        self.assertTrue(measurement.csv_file)
        self.assertTrue(measurement.csv_file.name.endswith('.csv'))

        # Check if peak potential and current were extracted correctly
        self.assertIsNotNone(measurement.peak_potelntial)
        self.assertAlmostEqual(measurement.peak_potelntial, 4.97582E-001, places=5)

        # Check if the peak current is correct 
        self.assertIsNotNone(measurement.peak_current)
        self.assertAlmostEqual(measurement.peak_current, 6.65984E-005, places=10)

    def test_invalid_file_handling(self):
        """
        Check that the parser handles invalid file and does not crash whole application.
        """
        bad_file = SimpleUploadedFile("garbage.DTA", b"This is not a valid .dta file content")

        measurement = Measurement.objects.create(
            electrode = self.electrode,
            technique = 'CV',
            date_performed = date.today(),
            raw_file = bad_file
        )
        measurement.refresh_from_db()
        # Should not have error 500, but should simply not create CSV or extract peaks
        self.assertFalse(measurement.csv_file)
        self.assertIsNone(measurement.peak_potelntial)
        self.assertIsNone(measurement.peak_current)

        

# Create your tests here.
