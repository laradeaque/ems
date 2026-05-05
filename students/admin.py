from django.contrib import admin
from .models import Grade, Learner

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'class_teacher')

@admin.register(Learner)
class LearnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'admission_number', 'grade')
