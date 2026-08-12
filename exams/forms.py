from .models import Exam, ExamCode, Subject
from students.models import Grade
from django.db import models
from django import forms
import datetime


STYLE = 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'


# forms.py
class DoubleClassMarklistForm(forms.Form):
    first_grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': STYLE})
    )

    second_grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': STYLE})
    )

    exam_code = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'AAA-BB0-0000',
            'class': STYLE
        })
    )

    show_points_only = forms.BooleanField(required=False)


def get_year_choices():
    current_year = datetime.date.today().year
    return [(y, str(y)) for y in range(current_year - 2, current_year + 5)]


class ExamCodeForm(forms.ModelForm):
    year = forms.ChoiceField(
        choices=get_year_choices,
        widget=forms.Select(attrs={'class': STYLE}),
        label="Year"
    )

    class Meta:
        model = ExamCode
        fields = ['name', 'term', 'year', 'exam_code', 'is_open']
        widgets = {
            'name': forms.Select(attrs={'class': STYLE}),
            'term': forms.Select(attrs={'class': STYLE}),
            'exam_code': forms.TextInput(attrs={'placeholder': 'e.g. EXAM-2026-T1', 'class': STYLE}),
            'is_open': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500'}),
        }
        labels = {
            'name': 'Exam Name',
            'term': 'Term',
            'exam_code': 'Exam Code',
            'is_open': 'Is Exam Open?',
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['code', 'grade', 'subject', 'date_taken']
        widgets = {
            'code': forms.Select(attrs={'class': STYLE, 'id': 'id_code'}),
            'grade': forms.Select(attrs={'class': STYLE, 'id': 'id_grade'}),
            'subject': forms.Select(attrs={'class': STYLE, 'id': 'id_subject'}),
            'date_taken': forms.DateInput(attrs={'class': STYLE, 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].queryset = ExamCode.objects.filter(is_open=True)
        self.fields['code'].empty_label = "-- Select Exam Code --"
        self.fields['grade'].empty_label = "-- Select Grade --"
        self.fields['subject'].empty_label = "-- Select Grade & Code First --"

        if 'grade' in self.data and 'code' in self.data:
            try:
                grade_id = int(self.data.get('grade'))
                code_id = int(self.data.get('code'))

                grade = Grade.objects.filter(id=grade_id).first()
                if grade:
                    existing_subject_ids = set(Exam.objects.filter(
                        grade_id=grade_id, code_id=code_id
                    ).values_list("subject_id", flat=True))

                    # Filter level logic in Python to maintain SQLite & Postgres compatibility
                    matching_ids = [
                        s.id for s in Subject.objects.all()
                        if (not s.levels or grade.level in s.levels)
                        and s.id not in existing_subject_ids
                    ]
                    self.fields['subject'].queryset = Subject.objects.filter(id__in=matching_ids).order_by("priority")
                else:
                    self.fields['subject'].queryset = Subject.objects.none()
            except (ValueError, TypeError):
                self.fields['subject'].queryset = Subject.objects.all()
        else:
            self.fields['subject'].queryset = Subject.objects.all()

class SubjectMarklistForm(forms.Form):
    grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': STYLE}),
    )

    exam_code = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'AAA-BB0-0000', 'class': STYLE})
    )

    subject = forms.CharField(
        widget=forms.TextInput(attrs={'class': STYLE})
    )



class ClassMarklistForm(forms.Form):
    grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': STYLE}),
    )

    exam_code = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'AAA-BB0-0000', 'class': STYLE})
    )

    show_points_only = forms.BooleanField(
        required=False,
        label="Show Points Only",
    )
