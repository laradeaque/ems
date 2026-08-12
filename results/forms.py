from django import forms
from students.models import Grade
from exams.models import ExamCode

class ReportForm(forms.Form):
    style = "w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none"

    grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={"class": style})
    )

    opener = forms.ModelChoiceField(
        queryset=ExamCode.objects.all(),
        widget=forms.Select(attrs={"class": style})
    )

    midterm = forms.ModelChoiceField(
        queryset=ExamCode.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": style})
    )

    endterm = forms.ModelChoiceField(
        queryset=ExamCode.objects.all(),
        widget=forms.Select(attrs={"class": style})
    )
