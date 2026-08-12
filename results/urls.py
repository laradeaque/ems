from django.urls import path
from . import views

urlpatterns = [
    # path("get-report-forms/", views.get_report_forms, name="get_report_forms"),
    path('get-report-forms/<int:grade_id>/', views.get_class_reports, name='get_class_reports'),
    path("learner-report/<int:learner_id>/", views.learner_report, name="learner_report"),
]
