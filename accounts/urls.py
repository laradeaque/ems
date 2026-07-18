from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('teacher/', views.teacher, name='teacher_url'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
