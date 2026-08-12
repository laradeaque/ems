from django.urls import path
from students import views

urlpatterns = [
    path('add/', views.add_student, name='add_learner'),
    path('list/', views.learners_list, name='learners_list'),

    # NEW
    path('grades/', views.grade_list, name='grade_list'),
    path('grades/add/', views.add_grade, name='add_grade'),
    path('grades/<int:grade_id>/', views.grade_detail, name='grade_detail'),
    path('<int:learner_id>/edit/', views.edit_learner, name="edit_learner"),
]
