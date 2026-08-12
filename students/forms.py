from django import forms
from .models import Learner


class LearnerForm(forms.ModelForm):
    class Meta:
        model = Learner
        fields = ["name", "admission_number", "grade"]
        style = "w-full p-2 border rounded focus:ring-2 \
        focus:ring-green-500 focus:outline-none"

        widgets = {
            "name": forms.TextInput(attrs={"class": style}),
            "admission_number": forms.TextInput(attrs={"class": style}),
            "grade": forms.Select(attrs={"class": style}),
        }

    def __init__(self, *args, **kwargs):
        admission = kwargs.pop("admission", None)
        super().__init__(*args, **kwargs)

        if admission:
            self.fields["admission_number"].initial = admission
