from django import forms
from .models import Learner

class LearnerForm(forms.ModelForm):
    class Meta:
        model = Learner
        fields = ['name', 'admission_number', 'grade']
