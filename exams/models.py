from django.db import models
from students.models import Grade
from django.conf import settings
from students.models import Learner


class ExamCode(models.Model):
    exam_code = models.CharField(max_length=20)
    date_taken = models.DateField(auto_now_add=True)
    is_open = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return self.exam_code

class Subject(models.Model):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=50)
    priority = models.PositiveIntegerField()

    class Meta:
        ordering = ["priority"]
        unique_together = ('code', 'name')

    def __str__(self):
        return f'{self.name} ({self.code})'

class Exam(models.Model):
    exam_code = models.CharField(max_length=20, null=True)  # old data
    code = models.ForeignKey(ExamCode, on_delete=models.CASCADE, blank=True, null=True) #backward compatibility
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=32)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, blank=True, null=True) # backward compatibility
    max_score = models.FloatField(blank=True, null=True, default=100)
    date_taken = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_final = models.BooleanField(default=False)  # ✅ NEW
    formula = models.TextField(blank=True, null=True)
    depends_on = models.ManyToManyField("self", blank=True, symmetrical=False)

    class Meta:
        unique_together = ('exam_code', 'grade', 'subject')

    @property
    def resolved_exam_code(self):
        return self.code.exam_code if self.code else self.exam_code

    def save(self, *args, **kwargs):
        if self.code:
            self.exam_code = self.code.exam_code
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.exam_code} {self.grade} {self.subject_name} out of {int(self.max_score)}'


class Mark(models.Model):
    student = models.ForeignKey(Learner, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.FloatField()

    class Meta:
        unique_together = ('student', 'exam')  # Prevent double entries

    def __str__(self):
        return f"{self.student.name} - {self.exam.exam_code} : {self.score}"

# TO DO
#
#
#
#
# USE THIS INSTEAD OF exam_code in views once we have the resolved_exam_code for
# BACKWARD COMPATIBILITY exam.resolved_exam_code
#
#
#
