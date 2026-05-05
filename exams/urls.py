from django.urls import path
from . import views

urlpatterns = [
    path('create_exam/', views.create_exam, name='create_exam'),
    path('create_exam_code/', views.create_exam_code, name='create_exam_code'),
    path('enter_marks/<int:exam_id>/', views.enter_marks, name='enter_marks'),
    path('subject_marklist/', views.subject_marklist_select, name='subject_marklist'),
    path('subject_marklist/results/', views.subject_marklist_results, name='subject_marklist_results'),
    path('class_marklist/', views.class_marklist, name='class_marklist'),
    path('class_marklist/results/', views.class_marklist_results, name='class_marklist_results'),
    path('ajax/get-exams/', views.get_exams_by_grade, name='get_exams_by_grade'),
    path('learner/<int:learner_id>/performance/', views.learner_performance, name='learner_performance'),
]
