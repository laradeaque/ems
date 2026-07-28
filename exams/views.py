from .forms import ExamForm, ExamCodeForm, DoubleClassMarklistForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from students.models import Learner, Grade
from .models import Exam, Mark, ExamCode, Subject
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db import models
from .utils import safe_eval

@login_required
def double_class_marklist(request):
    form = DoubleClassMarklistForm(request.POST or None)
    if request.user.role == "admin":
        exams = Exam.objects.all()
    else:
        exams = Exam.objects.filter(code__is_open=True)

    if request.method == "POST" and form.is_valid():
        data = {
            "first_grade": form.cleaned_data["first_grade"].id,
            "second_grade": form.cleaned_data["second_grade"].id,
            "exam_code": form.cleaned_data["exam_code"],
            "show_points_only": form.cleaned_data["show_points_only"],
        }

        request.session["double_class_data"] = data

        return redirect("double_results")

    return render(request, "double_classlist.html", {
        "form": form,
        "exams": exams
    })


@login_required
def double_class_results(request):
    """
    Page 2: Show Class Marklist results for two classes
    """
    data = request.session.get("double_class_data")
    if not data:
        return redirect("double")

    first_grade = get_object_or_404(
        Grade,
        id=data["first_grade"]
    )

    second_grade = get_object_or_404(
        Grade,
        id=data["second_grade"]
    )

    exam_code = data["exam_code"]
    show_points = data.get("show_points_only", False)

    # Fetch exams for both classes
    exams = Exam.objects.filter(
        grade__in=[first_grade, second_grade],
        is_final=True
    ).filter(
        models.Q(exam_code=exam_code) |
        models.Q(code__exam_code=exam_code)
    )

    # Unique subjects for table columns
    subjects = list(
        exams.values_list(
            "subject_name",
            flat=True
        ).distinct()
    )
    subjects = [
        subject.code
        for subject in Subject.objects.filter(exam__in=exams).distinct().order_by("priority")
    ]

    # All learners from both classes
    learners = Learner.objects.filter(
        grade__in=[first_grade, second_grade]
    ).select_related("grade")

    # Initialize totals
    subject_totals = {subject: 0 for subject in subjects}

    # Fetch all marks once
    all_marks = Mark.objects.filter(
        student__in=learners,
        exam__in=exams
    )

    # Fast lookup for marks
    mark_dict = {
        (m.student_id, m.exam_id): int(m.score)
        for m in all_marks
    }

    # Fast lookup for exams
    exam_lookup = {
        (exam.grade_id, exam.subject.code): exam.id
        for exam in exams
    }

    results = []

    for student in learners:
        student_data = {
            'student': student,
            'scores': {},
            'total': 0
        }

        total = 0

        for subject in subjects:

            # Get the correct exam for this student's class
            exam_id = exam_lookup.get(
                (student.grade_id, subject)
            )

            score = 0
            if exam_id:
                score = mark_dict.get(
                    (student.id, exam_id),
                    0
                )

            value = get_points(score) if show_points else score

            student_data['scores'][subject] = value

            total += value

            subject_totals[subject] += (
                value if show_points else score
            )

        student_data['total'] = total
        student_data['average'] = (
            total / len(subjects)
            if subjects else 0
        )

        results.append(student_data)

    # Compute means
    num_students = len(learners)

    subject_means = {
        subject: round(
            subject_totals[subject] / num_students,
            2
        ) if num_students > 0 else 0
        for subject in subjects
    }

    # Class stats
    class_total = sum(
        r['total']
        for r in results
    )

    class_mean = round(
        class_total / len(results),
        2
    ) if results else 0

    # Sort by total descending
    results.sort(
        key=lambda x: x['total'],
        reverse=True
    )

    return render(request, 'class_marklist.html', {
        'results': results,
        'subjects': subjects,
        'selected_grade': f"{first_grade.name} and {second_grade.name}",
        'exam_code': exam_code,
        'subject_totals': subject_totals,
        'subject_means': subject_means,
        'class_total': class_total,
        'class_mean': class_mean,
        'double': True,
        'show_points': show_points
    })

@login_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            #if int(exam.max_score) == int(100):
            exam.is_final = True

            exam.created_by = request.user
            existing_exam = Exam.objects.filter(
                exam_code=exam.code.exam_code,
                grade=exam.grade,
                #subject_name=exam.subject_name
                subject_name=exam.subject.code
            ).first()

            if existing_exam:
                messages.success(request, "Exam already exists. Opening marks entry...")
                return redirect('enter_marks', exam_id=existing_exam.id)
            else:
                exam.save()
                return redirect('enter_marks', exam_id=exam.id)
        else:
            messages.error(request, form.errors)
            code_present = ExamCode.objects.filter(is_open=True).exists()
            return render(request, 'create_exam.html', {'form': form, 'code_present': code_present})
    else:
        form = ExamForm()
        code_present = ExamCode.objects.filter(is_open=True).exists()
    return render(request, 'create_exam.html', {'form': form, 'code_present': code_present})


@login_required
def create_exam_code(request):
    if request.method == 'POST':
        form = ExamCodeForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.exam_code = request.POST.get('code')
            exam.save()
            return redirect('teacher_url')
        else:
            messages.error(request, form.errors)
            return render(request, 'create_exam_code.html', {'form': form})
    else:
        form = ExamCodeForm()
    return render(request, 'create_exam_code.html', {'form': form})


@login_required
def enter_marks(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    students = Learner.objects.filter(grade=exam.grade).order_by('name')

    # Fetch existing marks for this exam
    existing_marks = {
        mark.student_id: mark.score
        for mark in Mark.objects.filter(exam=exam)
    }

    if request.method == 'POST':
        for student in students:
            score = request.POST.get(f'score_{student.id}')

            if score:  # save only if value entered
                Mark.objects.update_or_create(
                    student=student,
                    exam=exam,
                    defaults={'score': float(score)}
                )
        messages.success(request, f'Exam {exam.subject.name}({exam.grade}) entered successfully!')
        return redirect('dashboard')

    return render(request, 'enter_marks.html', {
        'exam': exam,
        'students': students,
        'existing_marks': existing_marks  # 👈 pass this
    })


@login_required
def subject_marklist_select(request):
    from .forms import SubjectMarklistForm

    form = SubjectMarklistForm(request.POST or None)

    # ✅ Get unique grades sorted
    grades = Grade.objects.all().order_by('name')

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        data['exam'] = data['exam'].id
        data['subject'] = data['subject'].id
        request.session['subject_form_data'] = data
        return redirect('subject_marklist_results')

    return render(request, "subject_marklist_select.html", {
        "form": form,
        "grades": grades  # 👈 IMPORTANT
    })


@login_required
def subject_marklist_results(request):
    # Get form data from session
    data = request.session.get('subject_form_data')
    if not data:
        return redirect('subject_marklist')

    final_subject_name = ""
    results = []
    selected_exam = None
    total_score = 0
    learners = 0
    mean_score = 0

    selected_exam_id = data['exam']
    selected_exam = get_object_or_404(Exam, id=selected_exam_id)  # retrieve the object
    selected_subject = get_object_or_404(Subject, id=data["subject"])
    formula = data.get('formula')
    final_subject_name = data.get('paper_name', "")

    # ✅ Create/Get final exam if a new paper name is given
    if final_subject_name:
        final_exam, _ = Exam.objects.get_or_create(
            exam_code=selected_exam.exam_code,
            grade=selected_exam.grade,
            subject_name=final_subject_name,
            defaults={
                'max_score': 100,
                'date_taken': selected_exam.date_taken,
                'created_by': request.user,
                'is_final': True
            }
        )
    else:
        final_exam = selected_exam

    # ✅ Fetch exams & learners once
    exams = list(
        Exam.objects.filter(
            exam_code=final_exam.exam_code,
            grade=final_exam.grade,
            is_final=False
        ).select_related("subject")
    )
    students = list(Learner.objects.filter(grade=selected_exam.grade))

    # ✅ Fetch all marks at once
    all_marks = Mark.objects.filter(
        student__in=students,
        exam__in=exams if formula else [selected_exam]
    )

    # ✅ Build fast lookup
    mark_dict = {(m.student_id, m.exam_id): m.score for m in all_marks}

    marks_to_update = []
    # return

    for student in students:
        score = 0
        if formula:
            variables = {exam.subject.name: mark_dict.get((student.id, exam.id), 0)
                         for exam in exams}
            try:
                score = safe_eval(formula, variables)
            except Exception:
                score = 0
        else:
            score = mark_dict.get((student.id, selected_exam.id), 0)

        # Bulk update if final paper
        if final_subject_name:
            marks_to_update.append(Mark(student=student, exam=final_exam, score=float(score)))

        total_score += score
        learners += 1
        results.append({'student': student, 'score': int(round(score))})

    with transaction.atomic():
        if final_subject_name and marks_to_update:
            Mark.objects.bulk_create(
                marks_to_update,
                update_conflicts=True,
                update_fields=['score'],
                unique_fields=['student', 'exam']
            )

    if learners > 0:
        mean_score = round(total_score / learners, 2)

    return render(request, 'subject_marklist.html', {
        'results': results,
        'selected_exam': final_exam if final_subject_name else selected_exam,
        'total_score': int(total_score),
        'learners': learners,
        'mean_score': mean_score
    })


@login_required
def class_marklist(request):
    from .forms import ClassMarklistForm
    form = ClassMarklistForm(request.POST or None)

    if request.user.role == "admin":
        exams = Exam.objects.all()
    else:
        exams = Exam.objects.filter(code__is_open=True)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        # Store only IDs in session
        data['grade'] = data['grade'].id
        request.session['class_form_data'] = data
        return redirect('class_marklist_results')

    return render(request, "class_marklist_select.html", {
        "form": form,
        "exams": exams
    })


@login_required
def class_marklist_results(request):
    """
    Page 2: Show Class Marklist results
    """
    data = request.session.get('class_form_data')
    if not data:
        return redirect('class_marklist')

    grade_id = data['grade']
    exam_code = data['exam_code']

    # Fetch objects
    selected_grade = get_object_or_404(Grade, id=grade_id)
    exams = (
        Exam.objects.filter(grade=selected_grade, is_final=True)
        .filter(models.Q(exam_code=exam_code) | models.Q(code__exam_code=exam_code))
        .select_related("subject")
        .order_by("subject__priority")
    )
    exams = list(exams)

    subjects = [exam.subject.code for exam in exams]

    # Initialize totals
    subject_totals = {subject: 0 for subject in subjects}

    students = list(Learner.objects.filter(grade=selected_grade))

    # Fetch all marks once
    all_marks = Mark.objects.filter(
        student__in=students,
        exam__in=exams
    )

    # Build fast lookup dictionary
    mark_dict = {
        (m.student_id, m.exam_id): int(m.score)
        for m in all_marks
    }
    show_points = data.get('show_points_only', False)

    results = []
    for student in students:
        student_data = {'student': student, 'scores': {}, 'total': 0}
        total = 0
        for exam in exams:
            subject = exam.subject.code
            score = mark_dict.get((student.id, exam.id), 0)
            value = get_points(score) if show_points else score

            student_data['scores'][subject] = value
            total += value
            subject_totals[subject] += score if not show_points else value

        student_data['total'] = total
        student_data['average'] = total / len(exams) if exams else 0
        results.append(student_data)

    # Compute means
    num_students = len(students)
    subject_means = {
        subject: round(subject_totals[subject] / num_students, 2)
        if num_students > 0 else 0
        for subject in subjects
    }

    # Class stats
    class_total = sum(r['total'] for r in results)
    class_mean = round(class_total / len(results), 2) if results else 0

    # Sort results by total descending
    results.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'class_marklist.html', {
        'results': results,
        'subjects': subjects,
        'selected_grade': selected_grade,
        'exam_code': exam_code,
        'subject_totals': subject_totals,
        'subject_means': subject_means,
        'class_total': class_total,
        'class_mean': class_mean,
        'show_points': show_points
    })


@login_required
def learner_performance(request, learner_id):
    from students.models import Learner

    learner = get_object_or_404(Learner, id=learner_id)

    marks = (
        Mark.objects.filter(student=learner)
        .select_related("exam")
    )

    performance = {}

    for mark in marks:
        code = mark.exam.exam_code

        if code not in performance:
            performance[code] = {
                "total": 0,
                "count": 0,
                "date_taken": mark.exam.date_taken,
            }

        performance[code]["total"] += mark.score
        performance[code]["count"] += 1

    progress_data = []

    for code, data in performance.items():
        avg = data["total"] / data["count"]

        progress_data.append({
            "exam_code": code,
            "average": round(avg, 2),
            "date_taken": data["date_taken"].isoformat(),
        })

    # Sort newest to oldest
    progress_data = sorted(
        progress_data,
        key=lambda x: x["date_taken"],
        reverse=False
    )

    return render(request, "learner_performance.html", {
        "learner": learner,
        "progress_data": progress_data,
    })

@login_required
def get_exams_by_grade(request):
    grade_id = request.GET.get('grade_id')
    exams = Exam.objects.filter(grade_id=grade_id)

    data = [
        {
            'id': exam.id,
            'name': str(exam)
        }
        for exam in exams
    ]

    return JsonResponse({'exams': data})


@login_required
def get_exam_codes(request):
    grade_id = request.GET.get("grade")

    codes = (
        Exam.objects.filter(grade_id=grade_id)
        .values_list("exam_code", flat=True)
        .distinct()
        .order_by("exam_code")
    )

    return JsonResponse(list(codes), safe=False)


def get_points(score):
    if score >= 90:
        return 8
    elif score >= 75:
        return 7
    elif score >= 58:
        return 6
    elif score >= 41:
        return 5
    elif score >= 31:
        return 4
    elif score >= 21:
        return 3
    elif score >= 11:
        return 2
    else:
        return 1
