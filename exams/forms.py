from django import forms
from .models import Exam, ExamCode, Subject
from students.models import Grade

# forms.py

class DoubleClassMarklistForm(forms.Form):
    style = 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'

    first_grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': style})
    )

    second_grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': style})
    )

    exam_code = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'AAA-BB0-0000',
            'class': style
        })
    )

    show_points_only = forms.BooleanField(
        required=False
    )

class ExamCodeForm(forms.ModelForm):
    class Meta:
        model = ExamCode
        fields = ['code', "is_open"]

    code = forms.CharField(
        required=True,
        label="Exam Code",
        widget=forms.TextInput(attrs={
            'placeholder': 'XX-XX0-0000',
            'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
        })
    )
    is_open = forms.BooleanField(
        required=False,
        label="Is Exam Open?",
        widget=forms.CheckboxInput(attrs={
            'class': 'p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
        })
    )


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['code', 'grade', 'subject', 'date_taken']
        widgets = {
            'code': forms.Select(attrs={'class':'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'}),
            'grade': forms.Select(attrs={'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'}),
            'subject': forms.Select(attrs={'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'}),
            #'subject_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'}),
            #'max_score': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'}),
            'date_taken': forms.DateInput(attrs={'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].queryset = ExamCode.objects.filter(is_open=True)
        self.fields['subject'].queryset = Subject.objects.filter()


class SubjectMarklistForm(forms.Form):
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.select_related('grade')
        .order_by('grade__name', 'exam_code', 'subject_name'),
        label="Select Exam",
        widget=forms.Select(attrs={
            'class':
                'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }
        ),
    )

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(),
        label="Select subject",
        widget=forms.Select(attrs={
            'class':
                'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }
        ),
    )

    formula = forms.CharField(
        required=False,
        label="Formula (optional)",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. x*2 or (x/50)*100',
            'class': 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
        })
    )
    paper_name = forms.CharField(
        max_length=50,
        required=False,
        label="Enter Exam Name",
        widget=forms.TextInput(attrs={
            'class':
                'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
            }
        )
    )


class ClassMarklistForm(forms.Form):
    style = 'w-full p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
    grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        widget=forms.Select(attrs={'class': style}),
    )

    exam_code = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'AAA-BB0-0000',
            'class': style
        })
    )

    show_points_only = forms.BooleanField(
        required=False,
        label="Show Points Only",
        widget=forms.CheckboxInput(attrs={
            'class': 'p-2 border rounded focus:ring-2 focus:ring-blue-500 focus:outline-none'
        })
    )
