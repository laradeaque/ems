from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from students.models import Learner, Grade
from exams.models import Exam, ExamCode
from collections import defaultdict
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from .forms import RegisterForm
from datetime import timedelta
from .models import User

def reset_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        new_password = request.POST.get("new_password")
        admin_key = request.POST.get("admin_key")

        # check admin key first
        if admin_key != settings.ADMIN_CREATION_KEY:
            return render(request, "reset_password.html", {
                "error": "Invalid admin pass key"
            })
        try:
            user = User.objects.get(username=username)
            user.password = make_password(new_password)
            user.save()
            messages.success(request, "Password reset successful. Please log in.")
            return redirect("login")
        except User.DoesNotExist:
            return render(request, "reset_password.html", {
                "error": "User not found"
            })
    return render(request, "reset_password.html")

def close_expired_exam_codes():
    cutoff_date = timezone.now().date() - timedelta(days=14)

    ExamCode.objects.filter(
        is_open=True,
        date_taken__lt=cutoff_date
    ).update(is_open=False)


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
            messages.success(request, "Account created successfully.")
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
            messages.success(request, "Account logged in successfully.")
            return redirect('dashboard')
        else:
            error = "Invalid username or password"

    return render(request, 'login.html', {'error': error})


@login_required(login_url="/login/")
def dashboard(request):
    close_expired_exam_codes()
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
        #return render(request, "updates.html")
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

    if request.user.role != "admin":
        exams = exams.filter(created_by=request.user)

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
        'codes': ExamCode.objects.filter(is_open=True),
        'grades': Grade.objects.all(),
        'filters': {
            'code': code or '',
            'grade': grade or '',
            'subject': subject or ''
        }
    }

    return render(request, 'teacher.html', context)
