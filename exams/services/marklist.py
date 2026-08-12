from .helpers import build_mark_lookup, get_points
from exams.models import Exam, Mark
from students.models import Learner
from django.db import transaction
from exams.utils import safe_eval
from django.db import models



def generate_class_marklist_legacy(grades, exam_code, show_points=False):
    # Allow single grade or multiple grades
    if not isinstance(grades, list):
        grades = [grades,]

    exams = list(
        Exam.objects.filter(
            grade__in=grades,
            is_final=True
        )
        .filter(
            models.Q(exam_code=exam_code) |
            models.Q(code__exam_code=exam_code)
        )
        .select_related("subject")
        .order_by("subject__priority")
    )
    students = list(Learner.objects.filter(grade__in=grades))

    subjects = [exam.subject.code for exam in exams]
    # remove duplicates
    subjects = list(dict.fromkeys(subjects))

    subject_totals = {subject: 0 for subject in subjects}
    mark_lookup = build_mark_lookup(students, exams)

    results = []
    for student in students:
        student_data = {"student": student, "scores": {}, "total": 0}
        total = 0

        # Track how many exams belong to this specific student's grade for the average
        student_exam_count = 0

        for exam in exams:
            # FIX: Only process exams that belong to this student's specific grade
            if exam.grade_id != student.grade_id:
                continue

            student_exam_count += 1
            subject = exam.subject.code

            score = int(mark_lookup.get((student.id, exam.id), 0))
            value = get_points(score) if show_points else score

            student_data["scores"][subject] = value
            total += value

            subject_totals[subject] += value if show_points else score

        student_data["total"] = total

        # FIX: Divide by the exams for their specific class, not the combined length of both classes
        student_data["average"] = total / student_exam_count if student_exam_count else 0

        results.append(student_data)

    num_students = len(students)
    subject_means = {
        subject: round(subject_totals[subject] / num_students, 2) if num_students else 0
        for subject in subjects
    }

    class_total = sum(r["total"] for r in results)
    class_mean = round(class_total / len(results), 2) if results else 0

    results.sort(key=lambda x: x["total"], reverse=True)

    return {
        "results": results,
        "subjects": subjects,
        "subject_totals": subject_totals,
        "subject_means": subject_means,
        "class_total": class_total,
        "class_mean": class_mean,
    }


def generate_class_marklist(grades, exam_code, show_points=False):
    # Allow single grade or multiple grades
    if not isinstance(grades, list):
        grades = [grades,]

    exams = list(
        Exam.objects.filter(
            grade__in=grades,
            is_final=True
        )
        .filter(
            models.Q(exam_code=exam_code) |
            models.Q(code__exam_code=exam_code)
        )
        .select_related("subject")
        .order_by("subject__priority")
    )
    students = list(Learner.objects.filter(grade__in=grades))

    subjects = [exam.subject.code for exam in exams]
    # remove duplicates
    subjects = list(dict.fromkeys(subjects))

    subject_totals = {subject: 0 for subject in subjects}
    # Track the number of learners who actually sat for each subject (score > 0)
    subject_counts = {subject: 0 for subject in subjects}

    mark_lookup = build_mark_lookup(students, exams)

    results = []
    for student in students:
        student_data = {"student": student, "scores": {}, "total": 0}
        total = 0

        # Track how many exams belong to this specific student's grade
        student_exam_count = 0

        for exam in exams:
            # Only process exams that belong to this student's specific grade
            if exam.grade_id != student.grade_id:
                continue

            student_exam_count += 1
            subject = exam.subject.code

            score = int(mark_lookup.get((student.id, exam.id), 0))
            value = get_points(score) if show_points else score

            student_data["scores"][subject] = value
            total += value

            # EXCLUDE 0 MARKS: Only add to subject total and count if score > 0
            if score > 0:
                subject_totals[subject] += value if show_points else score
                subject_counts[subject] += 1

        student_data["total"] = total
        student_data["average"] = total / student_exam_count if student_exam_count else 0

        results.append(student_data)

    # Subject means divided ONLY by learners who sat for each subject (count > 0)
    subject_means = {
        subject: round(subject_totals[subject] / subject_counts[subject], 2) if subject_counts[subject] > 0 else 0
        for subject in subjects
    }

    class_total = sum(r["total"] for r in results)

    # EXCLUDE 0 TOTALS: Class mean divided ONLY by learners who took the exams (total > 0)
    sat_students_count = sum(1 for r in results if r["total"] > 0)
    class_mean = round(class_total / sat_students_count, 2) if sat_students_count > 0 else 0

    results.sort(key=lambda x: x["total"], reverse=True)

    return {
        "results": results,
        "subjects": subjects,
        "subject_totals": subject_totals,
        "subject_means": subject_means,
        "class_total": class_total,
        "class_mean": class_mean,
    }


def generate_subject_marklist(selected_exam, formula=None, final_subject_name="", created_by=None):
    # Create/Get final exam if paper name exists
    if final_subject_name:
        final_exam, _ = Exam.objects.get_or_create(
            exam_code=selected_exam.exam_code,
            grade=selected_exam.grade,
            subject_name=final_subject_name,
            defaults={
                'max_score': 100,
                'date_taken': selected_exam.date_taken,
                'created_by': created_by,
                'is_final': True
            }
        )
        exams = list(
            Exam.objects.filter(
                exam_code=final_exam.exam_code,
                grade=final_exam.grade,
                is_final=False
            ).select_related("subject")
        )
    else:
        exams = [selected_exam,]
        final_exam = selected_exam


    # Exams used for calculation
    print(final_exam.exam_code)
    print(selected_exam)
    print(exams)

    students = list(
        Learner.objects.filter(
            grade=selected_exam.grade
        )
    )

    mark_lookup = build_mark_lookup(students, exams)
    print(mark_lookup)

    results = []
    marks_to_update = []
    total_score = 0
    for student in students:
        score = 0

        if formula:
            variables = {
                exam.subject.name: mark_lookup.get((student.id, exam.id), 0)
                for exam in exams
            }

            try: score = safe_eval(formula, variables)
            except Exception: score = 0
        else:
            score = mark_lookup.get((student.id, selected_exam.id), 0)

        if final_subject_name:
            marks_to_update.append(
                Mark(student=student, exam=final_exam, score=float(score))
            )

        total_score += score
        results.append({
            "student": student,
            "score": int(round(score))
        })

    # Save generated final paper marks
    with transaction.atomic():
        if final_subject_name and marks_to_update:
            Mark.objects.bulk_create(
                marks_to_update,
                update_conflicts=True,
                update_fields=[
                    "score"
                ],
                unique_fields=[
                    "student",
                    "exam"
                ]
            )

    learners = len(students)
    mean_score = (
        round(total_score / learners, 2)
        if learners > 0
        else 0
    )

    return {
        "results": results,
        "selected_exam": (
            final_exam
            if final_subject_name
            else selected_exam
        ),
        "total_score": int(total_score),
        "learners": learners,
        "mean_score": mean_score
    }
