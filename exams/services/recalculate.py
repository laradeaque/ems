from django.db import transaction
from exams.models import Mark
from exams.utils import safe_eval
from exams.signal_state import disable_signals, enable_signals


def recalc_exam(final_exam):
    raw_exams = list(final_exam.depends_on.all())
    students = final_exam.grade.learner_set.all()

    # no need to continue if no formula
    if not final_exam.formula:
        return

    raw_marks = Mark.objects.filter(exam__in=raw_exams)

    mark_dict = {
        (m.student_id, m.exam_id): m.score
        for m in raw_marks
    }

    new_marks = []

    for student in students:
        variables = {
            ex.subject_name: mark_dict.get((student.id, ex.id), 0)
            for ex in raw_exams
        }

        try:
            score = safe_eval(final_exam.formula, variables)
        except Exception:
            score = 0

        new_marks.append(
            Mark(
                student=student,
                exam=final_exam,
                score=score
            )
        )

    with transaction.atomic():
        # 🚨 prevent signal recursion during delete + recreate
        disable_signals()

        try:
            Mark.objects.filter(exam=final_exam).delete()
            Mark.objects.bulk_create(new_marks)
        finally:
            enable_signals()
