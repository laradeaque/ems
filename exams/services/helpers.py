from exams.models import Mark


def build_mark_lookup(students, exams):
    marks = Mark.objects.filter(student__in=students, exam__in=exams)

    return {(m.student_id, m.exam_id): m.score for m in marks}


def save_marks(exam, students, post_data):
    saved = 0

    for student in students:
        score = post_data.get(f"score_{student.id}")

        if score:
            Mark.objects.update_or_create(
                student=student, exam=exam,
                defaults={"score":float(score)}
            )
            saved +=1

    return saved

def get_points(score):
    if score >= 90: return 8
    elif score >= 75: return 7
    elif score >= 58: return 6
    elif score >= 41: return 5
    elif score >= 31: return 4
    elif score >= 21: return 3
    elif score >= 11: return 2
    else: return 1
