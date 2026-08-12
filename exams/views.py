from .forms import ExamForm, ExamCodeForm, DoubleClassMarklistForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .services.performance import get_learner_performance
from .services.marklist import generate_subject_marklist
from .services.marklist import generate_class_marklist
from django.views.decorators.http import require_POST
from .services.helpers import get_points, save_marks
from .models import Exam, Mark, ExamCode, Subject
from students.decorators import role_required
from django.core.paginator import Paginator
from students.models import Learner, Grade
from .forms import SubjectMarklistForm
from .forms import ClassMarklistForm
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db import models
from .utils import safe_eval


# exam/views.py
@role_required("admin")
def exam_codes(request):
    search_query = request.GET.get('q', '').strip()

    # Query with optional search filter and latest ordering
    codes = ExamCode.objects.all().order_by('-id')
    if search_query:
        codes = codes.filter(
            Q(exam_code__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )

    # Paginate 10 items per page
    paginator = Paginator(codes, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, "exam_codes.html", context)


@role_required("admin")
def create_exam_code(request):
    if request.method == "POST":
        form = ExamCodeForm(request.POST)
        if form.is_valid():
            code = form.save(commit=False)
            code.created_by = request.user
            code.save()
            messages.success(request, f"Exam Code '{code.exam_code}' created successfully.")
            return redirect('exam_codes')
    else:
        form = ExamCodeForm()

    return render(request, "create_exam_code.html", {
        "form": form,
        "edit_mode": False
    })


@role_required("admin")
def edit_exam_code(request, pk):
    code = get_object_or_404(ExamCode, pk=pk)
    if request.method == "POST":
        form = ExamCodeForm(request.POST, instance=code)
        if form.is_valid():
            form.save()
            messages.success(request, f"Exam Code '{code}' updated successfully.")
            return redirect('exam_codes')
    else:
        form = ExamCodeForm(instance=code)

    return render(request, "create_exam_code.html", {
        "form": form,
        "edit_mode": True,
        "code": code
    })


@role_required("admin")
@require_POST
def delete_exam_code(request, pk):
    code = get_object_or_404(ExamCode, pk=pk)
    code_name = code.exam_code
    code.delete()
    messages.success(request, f"Exam Code '{code_name}' was deleted successfully.")
    return redirect('exam_codes')


@role_required("admin")
def learner_performance(request, learner_id):
    learner = get_object_or_404(Learner, id=learner_id)

    progress_data = get_learner_performance(learner)
    return render(request, "learner_performance.html", {
        "learner": learner,
        "progress_data": progress_data
    })


@role_required("admin", "teacher")
def get_exams_by_grade(request):
    grade_id = request.GET.get('grade_id')
    try: grade_id = int(grade_id)
    except ValueError: return JsonResponse([], safe=True)

    exams = Exam.objects.filter(grade_id=grade_id)
    data = [{'id': exam.id, 'name': str(exam)} for exam in exams]
    return JsonResponse({'exams': data})


@role_required("admin", "teacher")
def get_exam_codes(request):
    grade_id = request.GET.get("grade")
    try: grade_id = int(grade_id)
    except ValueError: return JsonResponse([], safe=True)

    codes = (
        Exam.objects.filter(grade_id=grade_id)
        .values_list("exam_code", flat=True)
        .distinct()
        .order_by("exam_code")
    )

    return JsonResponse(list(codes), safe=False)


@role_required("admin", "teacher")
def get_subjects(request):
    grade_id = request.GET.get("grade")
    try: grade_id = int(grade_id)
    except ValueError: return JsonResponse({}, safe=True)

    exam_code = request.GET.get("exam_code")

    exams = Exam.objects.filter(
        grade_id=grade_id, exam_code=exam_code
        ).select_related("subject").order_by("subject__priority")

    subjects = [
        exam.subject.name if exam.subject else exam.subject_name
        for exam in exams
    ]
    subjects = list(dict.fromkeys(subjects))

    return JsonResponse(subjects, safe=False)


@role_required("admin")
def double_class_marklist(request):
    form = DoubleClassMarklistForm(request.POST or None)
    exams = Exam.objects.all()

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


@role_required("teacher")
def create_exam_legacy(request):
    '''
    This is for teachers only admin is to manage only.
    The marks must be out of 100
    '''
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
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


@role_required("admin", "teacher")
def enter_marks(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    students = (Learner.objects.filter(grade=exam.grade).order_by("name"))

    existing_marks = {m.student_id: m.score for m in Mark.objects.filter(exam=exam)    }

    if request.method=="POST":
        _ = save_marks(exam, students, request.POST)

        messages.success(request, "Marks saved successfully")
        return redirect("dashboard")

    return render(request, "enter_marks.html", {
        "exam": exam,
        "students": students,
        "existing_marks": existing_marks  # 👈 pass this
    })


@role_required("admin")
def class_marklist(request):
    form = ClassMarklistForm(request.POST or None)
    exams = Exam.objects.all()

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


@role_required("admin")
def class_marklist_results(request):
    data = request.session.get('class_form_data')
    if not data:
        return redirect('class_marklist')

    grade_id = data['grade']
    exam_code = data['exam_code']

    # Fetch objects
    selected_grade = get_object_or_404(Grade, id=grade_id)
    show_points = data.get("show_points_only", False)

    context = generate_class_marklist(selected_grade, data["exam_code"], show_points)
    return render(request, "class_marklist.html", {
        **context,
        "selected_grade": selected_grade,
        "exam_code": data["exam_code"],
        "show_points": show_points
    })


@role_required("admin")
def subject_marklist_select(request):
    form = SubjectMarklistForm(request.POST or None)
    grades = Grade.objects.all().order_by('name')

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        data['grade'] = data["grade"].id
        subject = data['subject']
        print(subject)
        data['exam'] = Exam.objects.filter(
                            grade_id=data['grade'],
                            exam_code=data['exam_code']
                     ).filter(
                         models.Q(subject__name=subject) |
                         models.Q(subject_name=subject)
                     ).first().id
        request.session['subject_form_data'] = data
        return redirect('subject_marklist_results')

    return render(request, "subject_marklist_select.html", {
        "form": form,
        "grades": grades  # 👈 IMPORTANT
    })


@role_required("admin")
def subject_marklist_results(request):
    data = request.session.get('subject_form_data')
    if not data:
        return redirect('subject_marklist')

    selected_exam = get_object_or_404(Exam, id=data['exam'])
    result = generate_subject_marklist(
        selected_exam=selected_exam,
        formula=data.get('formula', ""),
        final_subject_name=data.get('paper_name', ""),
        created_by=request.user
    )
    # print(f"{result}")
    # return JsonResponse("Good Boy", safe=False)

    return render(request, 'subject_marklist.html', result)


@role_required("admin")
def double_class_results(request):
    data = request.session.get("double_class_data")
    if not data:
        return redirect("double")

    first_grade = get_object_or_404(Grade, id=data["first_grade"])
    second_grade = get_object_or_404(Grade, id=data["second_grade"])
    exam_code = data["exam_code"]
    show_points = data.get("show_points_only", False)

    result = generate_class_marklist(
        grades=[first_grade, second_grade],
        exam_code=exam_code,
        show_points=show_points
    )

    return render(request, "class_marklist.html", {
        **result,
        "selected_grade": f"{first_grade.name} and {second_grade.name}",
        "exam_code": exam_code,
        "double": True,
        "show_points": show_points
    })


@role_required("admin", "teacher")
def get_available_subjects(request):
    """
    Returns only subjects that:
    1. Belong to the requested Grade's Education Level (or apply to all levels).
    2. Have NOT yet had an Exam created for this specific grade + exam code combination.
    """
    grade_id = request.GET.get("grade_id")
    code_id = request.GET.get("code_id")

    if not grade_id or not code_id:
        return JsonResponse([], safe=False)

    try:
        grade_id = int(grade_id)
        grade = Grade.objects.get(id=grade_id)
    except (ValueError, Grade.DoesNotExist):
        return JsonResponse([], safe=False)

    # 1. Get subjects that already have an exam created for this grade and code
    existing_exam_subject_ids = set(
        Exam.objects.filter(
            grade_id=grade_id
        ).filter(
            models.Q(code_id=code_id) | models.Q(exam_code=code_id) | models.Q(code__exam_code=code_id)
        ).values_list("subject_id", flat=True)
    )

    existing_subject_names = set(
        Exam.objects.filter(
            grade_id=grade_id
        ).filter(
            models.Q(code_id=code_id) | models.Q(exam_code=code_id) | models.Q(code__exam_code=code_id)
        ).values_list("subject_name", flat=True)
    )

    # 2. Filter subjects in Python (100% database-agnostic across SQLite, Postgres, and MySQL)
    available_subjects = [
        s for s in Subject.objects.all().order_by("priority")
        if (not s.levels or grade.level in s.levels)
        and s.id not in existing_exam_subject_ids
        and s.code not in existing_subject_names
    ]

    data = [{'id': s.id, 'name': f"{s.name} ({s.code})"} for s in available_subjects]
    return JsonResponse(data, safe=False)


@role_required("admin", "teacher")
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.is_final = True
            exam.created_by = request.user
            exam.subject_name = exam.subject.code

            existing_exam = Exam.objects.filter(
                code=exam.code,
                grade=exam.grade,
                subject=exam.subject
            ).first()

            if existing_exam:
                messages.info(request, "Exam already exists. Opening marks entry...")
                return redirect('enter_marks', exam_id=existing_exam.id)
            else:
                exam.save()
                messages.success(request, f"Exam for {exam.subject.name} created successfully!")
                return redirect('enter_marks', exam_id=exam.id)
        else:
            messages.error(request, "Please correct the errors below.")
            code_present = ExamCode.objects.filter(is_open=True).exists()
            return render(request, 'create_exam.html', {'form': form, 'code_present': code_present})
    else:
        form = ExamForm()
        code_present = ExamCode.objects.filter(is_open=True).exists()
    return render(request, 'create_exam.html', {'form': form, 'code_present': code_present})


@role_required("admin")
@require_POST
def delete_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam_info = f"{exam.resolved_exam_code} - {exam.grade.name} ({exam.subject_name})"

    exam.delete()

    messages.success(request, f"Exam '{exam_info}' was deleted successfully.")

    # Redirect back to the same page with existing filters/pagination intact
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('teacher_url')
