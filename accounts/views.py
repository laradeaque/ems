from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from students.models import Learner, Grade
from exams.models import Exam, ExamCode
from django.db.models import Prefetch
from collections import defaultdict
from django.contrib import messages
from .forms import RegisterForm
from .models import User


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            error = "Invalid username or password"

    return render(request, 'login.html', {'error': error})


@login_required(login_url="/login/")
def dashboard(request):
    if request.user.role == 'admin':
        total_learners = Learner.objects.count()
        classes = Grade.objects.count()
        users = User.objects.count()
        user_active = User.objects.filter(is_active=True).count()

        return render(request, 'admin.html', {
            'total_learners': total_learners,
            'users': users,
            'users_active': user_active,
            'classes': classes
        })
    else:
        return teacher(request)

@login_required(login_url="/login/")
def teacher(request):
    exams = Exam.objects.select_related('grade').order_by('-date_taken')

    # 🔍 FILTERS
    code = request.GET.get('code')
    grade = request.GET.get('grade')
    subject = request.GET.get('subject')

    if code:
        exams = exams.filter(code_id=code)

    if grade:
        exams = exams.filter(grade_id=grade)

    if subject:
        exams = exams.filter(subject_name__icontains=subject)

    # 📄 PAGINATION (10 per page)
    paginator = Paginator(exams, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 📦 GROUP BY exam_code
    grouped_exams = defaultdict(list)
    for exam in page_obj:
        grouped_exams[exam.exam_code].append(exam)

    context = {
        'page_obj': page_obj,
        'grouped_exams': dict(grouped_exams),
        'codes': ExamCode.objects.all(),
        'grades': Grade.objects.all(),
        'filters': {
            'code': code or '',
            'grade': grade or '',
            'subject': subject or ''
        }
    }

    return render(request, 'teacher.html', context)
