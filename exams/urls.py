from django.urls import path
from . import views

# urls.py
urlpatterns = [
    path('exam-codes/', views.exam_codes, name='exam_codes'),
    path('exam-codes/create/', views.create_exam_code, name='create_exam_code'),
    path('exam-codes/<int:pk>/edit/', views.edit_exam_code, name='edit_exam_code'),
    path('exam-codes/<int:pk>/delete/', views.delete_exam_code, name='delete_exam_code'),
    path('create_exam/', views.create_exam, name='create_exam'),
    path('enter_marks/<int:exam_id>/', views.enter_marks, name='enter_marks'),
    path('subject_marklist/', views.subject_marklist_select, name='subject_marklist'),
    path('subject_marklist/results/', views.subject_marklist_results, name='subject_marklist_results'),
    path('class_marklist/', views.class_marklist, name='class_marklist'),
    path('double_class_marklist/', views.double_class_marklist, name='double'),
    path('double_class_results/', views.double_class_results, name='double_results'),
    path('class_marklist/results/', views.class_marklist_results, name='class_marklist_results'),
    path('ajax/get-exams/', views.get_exams_by_grade, name='get_exams_by_grade'),
    path('learner/<int:learner_id>/performance/', views.learner_performance, name='learner_performance'),
    path("ajax/exam-codes/", views.get_exam_codes, name="get_exam_codes"),
    path("ajax/subjects/", views.get_subjects, name="get_subjects"),
    path('get-available-subjects/', views.get_available_subjects, name='get_available_subjects'),
    path('delete/<int:pk>//', views.delete_exam, name='delete_exam'),
]
