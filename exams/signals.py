from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from exams.models import Mark, Exam
from exams.services.recalculate import recalc_exam
from exams.signal_state import signals_enabled


def trigger_recalc(raw_exam):
    # 🚨 prevent recursion trigger
    if not signals_enabled():
        return

    final_exams = Exam.objects.filter(
        is_final=True,
        depends_on=raw_exam
    )

    for final_exam in final_exams:
        # ensure DB commit before recalculation
        transaction.on_commit(lambda e=final_exam: recalc_exam(e))


@receiver(post_save, sender=Mark)
def mark_saved(sender, instance, **kwargs):
    trigger_recalc(instance.exam)


@receiver(post_delete, sender=Mark)
def mark_deleted(sender, instance, **kwargs):
    trigger_recalc(instance.exam)
