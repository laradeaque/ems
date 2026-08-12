from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from weasyprint import HTML

from students.decorators import role_required
from students.models import Grade, Learner

from .utils import lookup_class, lookup_learner


@role_required("admin")
def get_class_reports(request, grade_id):
    """Generates a combined multi-page PDF for all learners in a grade."""
    grade = get_object_or_404(Grade, id=grade_id)
    class_reports = lookup_class(grade)

    if not class_reports:
        messages.warning(request, f"No exam mark data found for {grade.name}.")
        return HttpResponse("No exam mark data found for this grade.", status=404)

    context = {
        "grade": grade,
        "class_reports": class_reports,
    }

    html_string = render_to_string("REPORT_TEMPLATE.html", context)

    pdf_bytes = HTML(
        string=html_string, base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{grade.name}_Class_Reports.pdf"'
    return response


@role_required("admin")
def learner_report(request, learner_id):
    """Generates a single PDF report for an individual learner using the unified template."""
    learner = get_object_or_404(Learner, id=learner_id)
    learner_details = lookup_learner(learner)

    if not learner_details:
        return HttpResponse("No mark data available for this learner.", status=404)

    # Wrap the single learner in class_reports list so the same template handles both views
    context = {
        "grade": learner.grade,
        "class_reports": [{"learner": learner, "values": learner_details}],
    }

    html_string = render_to_string("REPORT_TEMPLATE.html", context)
    pdf_bytes = HTML(
        string=html_string, base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{learner.name}_Report.pdf"'

    return response
