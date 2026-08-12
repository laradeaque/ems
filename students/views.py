from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .decorators import role_required
from django.contrib import messages
from .models import Learner, Grade
from accounts.models import User
from .forms import LearnerForm
import uuid


@role_required("admin")
def edit_learner(request, learner_id):
    learner = get_object_or_404(Learner, id=learner_id)

    if request.method == "POST":
        form = LearnerForm(request.POST, instance=learner)

        if form.is_valid():
            form.save()
            messages.success(request, "Learner updated successfully.")
            return redirect("learners_list")

    else:
        form = LearnerForm(instance=learner)

    return render(request, "edit_student.html", {
        "form": form,
        "learner": learner,
    })


@role_required("admin")
def add_student(request):
    admission = uuid.uuid4().hex[:12].upper()
    if request.method == "POST":
        form = LearnerForm(request.POST)

        if form.is_valid():
            learner = form.save()
            messages.success(request, f"{learner.name} added successfully.")

            return redirect("add_learner")
    else:
        form = LearnerForm(admission=admission)

    return render(request, "add_student.html", {
        "form": form
    })


@role_required("admin")
def grade_list(request):
    grades = Grade.objects.all()

    # 📄 PAGINATION (10 per page)
    paginator = Paginator(grades, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'list_grades.html', context)


@role_required("admin")
def add_grade(request):
    teachers = User.objects.filter(role='teacher')

    if request.method == "POST":
        name = request.POST.get("name")
        teacher_id = request.POST.get("class_teacher")

        if name:
            teacher = User.objects.filter(id=teacher_id).first() if teacher_id else None
            Grade.objects.create(name=name, class_teacher=teacher)

            messages.success(request, f"Grade {name} created successfully!")
            return redirect('grade_list')
        else:
            messages.error(request, "Grade name is required.")

    return render(request, 'add_grade.html', {"teachers": teachers})

@role_required("admin")
def grade_detail(request, grade_id):
    grade = get_object_or_404(Grade, id=grade_id)
    learners = Learner.objects.select_related('grade').filter(grade=grade)

    # 📄 PAGINATION (10 per page)
    paginator = Paginator(learners, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'grade_name': grade.name
    }
    return render(request, 'grade_details.html', context)


@role_required("admin")
def learners_list(request):
    grades = Grade.objects.all()
    learners = Learner.objects.select_related('grade').all()

    # 🔍 FILTERS
    grade_id = request.GET.get('grade', '')
    learner_name = request.GET.get('learner_name', '')

    learners = learners.filter(grade_id=grade_id) if grade_id else learners
    learners = learners.filter(name__icontains=learner_name) if learner_name else learners

    # 📄 PAGINATION (10 per page)
    paginator = Paginator(learners, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)


    context = {
        'page_obj': page_obj,
        'grades': grades,
        'filters': {
            'selected_grade': grade_id or '',
            'learner_name': learner_name or ''
        }
    }
    return render(request, 'list_learners.html', context)
