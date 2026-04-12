from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from .models import Project, Biomarker, Electrode

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
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'style': 'border: 1px solid black;',
            })
        }

class BiomarkerForm(forms.ModelForm):
    class Meta:
        model = Biomarker
        fields = ['name']
        labels = {
            'name': 'Nazwa biomarkera',
        }

class ElectrodeForm(forms.ModelForm):
    class Meta:
        model = Electrode
        fields = ['label', 'material']
        labels = {
            'label': 'Etykieta elektrody',
            'material': 'Materiał elektrody (opcjonalnie)',
        }