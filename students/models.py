from django.conf import settings
from django.db import models
import uuid


class Grade(models.Model):
    name = models.CharField(max_length=50, unique=True)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, #limit_choices_to={'role': 'teacher'}  # only teachers
    )

    def __str__(self):
        return self.name


class Learner(models.Model):
    name = models.CharField(max_length=100)
    admission_number = models.CharField(max_length=12, unique=True)
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({self.grade})"
