from django.contrib.auth.decorators import login_required
from .utils import get_placeholders, lookup
from .utils import generate_class_reports
from django.http import FileResponse
from .utils import get_template_path
from django.shortcuts import render
from .forms import ReportForm
from pathlib import Path


@login_required
def get_report_forms(request):
    form = ReportForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        grade = form.cleaned_data["grade"]

        exam_codes = (
            form.cleaned_data["opener"].exam_code,
            form.cleaned_data["midterm"].exam_code,
            form.cleaned_data["endterm"].exam_code,
        )
        template_path = get_template_path(grade)
        placeholders = get_placeholders(docx_path=template_path)
        reports = lookup(exam_codes, grade, placeholders)
        file = generate_class_reports(template_path, reports)

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{grade.name} Report Forms.docx"
        )


    return render(request, "get_report_forms.html", {
        "form": form
    })

