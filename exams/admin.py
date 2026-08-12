from django import forms
from django.contrib import admin
from students.models import Grade
from .models import Subject, ExamCode, Exam, Mark


class SubjectAdminForm(forms.ModelForm):
    levels = forms.MultipleChoiceField(
        choices=Grade.Level.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select levels where this learning area is offered. If none selected, it applies to all levels."
    )

    class Meta:
        model = Subject
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.levels:
            self.initial['levels'] = self.instance.levels

    def clean_levels(self):
        return self.cleaned_data.get('levels', [])


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    form = SubjectAdminForm
    list_display = ('name', 'code', 'priority', 'get_levels_display')
    search_fields = ('name', 'code')

    def get_levels_display(self, obj):
        if not obj.levels:
            return "All Levels"
        level_dict = dict(Grade.Level.choices)
        return ", ".join([level_dict.get(lvl, lvl) for lvl in obj.levels])

    get_levels_display.short_description = "Target Levels"


admin.site.register(ExamCode)
admin.site.register(Exam)
admin.site.register(Mark)
