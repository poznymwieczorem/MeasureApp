from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from .models import Project, Biomarker, Electrode, Measurement


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Wymagany do weryfikacji konta.")
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ten adres e-mail jest już zajęty.")
        return email


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']
        labels = {
            'name': 'Nazwa projektu',
            'description': 'Opis projektu',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'border: 1px solid black;',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'style': 'border: 1px solid black;',
            }),
        }


class BiomarkerForm(forms.ModelForm):
    class Meta:
        model = Biomarker
        fields = ['name']
        labels = {'name': 'Nazwa biomarkera'}
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ElectrodeForm(forms.ModelForm):
    class Meta:
        model = Electrode
        fields = ['label', 'material']
        labels = {
            'label': 'Etykieta elektrody',
            'material': 'Materiał elektrody (opcjonalnie)',
        }
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MeasurementForm(forms.ModelForm):
    class Meta:
        model = Measurement
        fields = ['electrode', 'biomarker', 'technique', 'date_performed', 'raw_file']
        labels = {
            'electrode': 'Elektroda',
            'biomarker': 'Biomarker',
            'technique': 'Metoda pomiaru',
            'date_performed': 'Data i godzina pomiaru',
            'raw_file': 'Plik .DTA',
        }
        widgets = {
            'date_performed': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['electrode'].queryset = project.electrodes.all()
            self.fields['biomarker'].queryset = project.biomarkers.all()
        self.fields['date_performed'].input_formats = ['%Y-%m-%dT%H:%M']


class MeasurementSearchForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        label='Data od',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    date_to = forms.DateField(
        required=False,
        label='Data do',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    electrode = forms.ModelChoiceField(
        queryset=Electrode.objects.none(),
        required=False,
        label='Elektroda',
        empty_label='Wszystkie elektrody',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    biomarker = forms.ModelChoiceField(
        queryset=Biomarker.objects.none(),
        required=False,
        label='Biomarker',
        empty_label='Wszystkie biomarkery',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields['electrode'].queryset = project.electrodes.all()
            self.fields['biomarker'].queryset = project.biomarkers.all()
