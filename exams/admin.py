from django.contrib import admin
from .models import Exam, ExamCode, Mark


# Register your models here.
admin.site.register(Exam)
admin.site.register(ExamCode)
admin.site.register(Mark)
