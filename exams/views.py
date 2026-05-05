from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ExamForm, ExamCodeForm
from .models import Exam, Mark
from students.models import Learner, Grade
from .utils import safe_eval
import time
from django.http import JsonResponse
from django.db import transaction
from django.db import models
from django.contrib import messages


@login_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            if int(exam.max_score) == int(100):
                exam.is_final = True
            exam.created_by = request.user
            exam.save()
            return redirect('enter_marks', exam_id=exam.id)
        else:
            messages.error(request, form.errors)
            return render(request, 'create_exam.html', {'form': form})
    else:
        form = ExamForm()
    return render(request, 'create_exam.html', {'form': form})


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
        messages.success(request, f'Exam {exam.subject_name} entered successfuly!')
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
    formula = data.get('formula')
    final_subject_name = data.get('paper_name', "")
    print(formula)

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
    exams = list(Exam.objects.filter(
        exam_code=final_exam.exam_code,
        grade=final_exam.grade,
        is_final=False
    ))
    print(exams)
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
            variables = {exam.subject_name: mark_dict.get((student.id, exam.id), 0)
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
    exams = Exam.objects.filter(is_final=True)
    exams = exams.filter(code__is_open=True)

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
    exams = Exam.objects.filter(
        grade=selected_grade,
        is_final=True
    )
    exams = exams.filter(
        models.Q(exam_code=code) | models.Q(code__exam_code=code)
    )
    exams = list(exams)

    subjects = [exam.subject_name for exam in exams]

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
            subject = exam.subject_name
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
    from exams.models import Mark, Exam
    from students.models import Learner
    from django.db.models import Avg

    learner = get_object_or_404(Learner, id=learner_id)

    # Get all exams for this learner
    marks = Mark.objects.filter(student=learner).select_related('exam')

    # Group by exam_code (important for progress)
    performance = {}

    for mark in marks:
        code = mark.exam.exam_code

        if code not in performance:
            performance[code] = {
                'total': 0,
                'count': 0
            }

        performance[code]['total'] += mark.score
        performance[code]['count'] += 1

    # Convert to list
    progress_data = []
    for code, data in performance.items():
        avg = data['total'] / data['count']
        progress_data.append({
            'exam_code': code,
            'average': round(avg, 2)
        })

    # Sort by exam_code (or date later)
    progress_data = sorted(progress_data, key=lambda x: x['exam_code'])
    progress_data.reverse()

    return render(request, 'learner_performance.html', {
        'learner': learner,
        'progress_data': progress_data
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
