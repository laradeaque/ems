from django.conf import settings
from django.db import models


class Grade(models.Model):
    class Level(models.TextChoices):
        NURSERY = "NURSERY", "Nursery"
        LOWER_PRIMARY = "LOWER_PRIMARY", "Lower Primary"
        UPPER_PRIMARY = "UPPER_PRIMARY", "Upper Primary"
        JUNIOR_SCHOOL = "JUNIOR_SCHOOL", "Junior School"

    name = models.CharField(max_length=50, unique=True)
    level = models.CharField(max_length=20, choices=Level.choices)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        # limit_choices_to={"role": "teacher"}
    )

    def __str__(self):
        return f"{self.name} {self.level}"


class Learner(models.Model):
    name = models.CharField(max_length=100)
    admission_number = models.CharField(max_length=12, unique=True)
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} ({self.grade})"
