from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Learner, Grade
from accounts.models import User
import uuid


@login_required
def add_student(request):
    s_id = uuid.uuid4().hex[:12].upper()
    if request.user.role != 'admin':
        return redirect('dashboard')

    grades = Grade.objects.all()  # Fetch all grades from DB

    if request.method == "POST":
        name = request.POST.get("name")
        admission_number = request.POST.get("admission_number")
        grade_id = request.POST.get("grade")

        if not (name and admission_number and grade_id):
            messages.error(request, "All fields are required.")
        else:
            try:
                grade_obj = get_object_or_404(Grade, id=grade_id)
                learner = Learner.objects.create(
                    name=name,
                    admission_number=admission_number,
                    grade=grade_obj
                )
                learner.save()
                messages.success(request, f"Learner {name} added successfully!")
                return redirect('add_learner')
            except Grade.DoesNotExist:
                messages.error(request, "Selected grade does not exist.")
            except Exception as e:
                messages.error(request, f"Error adding learner: {str(e)}")

    return render(request, 'add_student.html', {
        "lid": s_id,
        "grades": grades
    })


@login_required
def grade_list(request):
    if request.user.role != 'admin':
        return redirect('dashboard')

    grades = Grade.objects.all()

    return render(request, 'list_grades.html', {
        'grades': grades
    })


@login_required
def add_grade(request):
    if request.user.role != 'admin':
        return redirect('dashboard')

    teachers = User.objects.filter(role='teacher')

    if request.method == "POST":
        name = request.POST.get("name")
        teacher_id = request.POST.get("class_teacher")

        if not name:
            messages.error(request, "Grade name is required.")
        else:
            teacher = None
            if teacher_id:
                teacher = User.objects.filter(id=teacher_id).first()

            Grade.objects.create(
                name=name,
                class_teacher=teacher
            )

            messages.success(request, f"Grade {name} created successfully!")
            return redirect('grade_list')

    return render(request, 'add_grade.html', {
        "teachers": teachers
    })

@login_required
def grade_detail(request, grade_id):
    if request.user.role != 'admin':
        return redirect('dashboard')

    grade = get_object_or_404(Grade, id=grade_id)
    learners = Learner.objects.select_related('grade').all()
    learners = learners.filter(grade=grade)
    teachers = User.objects.filter(role='teacher')

    if request.method == "POST":
        teacher_id = request.POST.get("class_teacher")

        if teacher_id:
            grade.class_teacher = get_object_or_404(User, id=teacher_id)
        else:
            grade.class_teacher = None

        grade.save()
        messages.success(request, "Class teacher updated.")
        return redirect('grade_detail', grade_id=grade.id)

    return render(request, 'grade_details.html', {
        'grade': grade,
        'learners': learners,
        'teachers': teachers
    })


@login_required(login_url="/login/")
def learners_list(request):
    grades = Grade.objects.all()
    learners = Learner.objects.select_related('grade').all()

    # 🔍 FILTERS
    grade_id = request.GET.get('grade', '')
    learner_name = request.GET.get('learner_name', '')
    print(learner_name)

    if grade_id:
        learners = learners.filter(grade_id=grade_id)

    if learner_name:
        learners = learners.filter(name__icontains=learner_name)

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
