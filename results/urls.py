from django.urls import path
from . import views

urlpatterns = [
    path("get-report-forms/", views.get_report_forms, name="get_report_forms"),
]