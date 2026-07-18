from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import FileResponse
from django.conf import settings
from exams.models import Exam, Mark, ExamCode
from students.models import Learner, Grade
from .utils import get_placeholders
from .forms import ReportForm
from copy import deepcopy
from docx import Document
from io import BytesIO
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


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

        filename = "PLAY.docx"
        template_path = BASE_DIR / filename

        placeholders = get_placeholders(docx_path=template_path)

        reports = lookup(exam_codes, grade, placeholders)

        file = generate_class_reports(template_path, reports)

        return FileResponse(
            file,
            as_attachment=True,
            filename=f"{grade.name} Report Forms.docx"
        )

    return render(request, "get_reportforms.html", {
        "form": form
    })


def lookup(exam_codes, grade, placeholders):
    learners = list(Learner.objects.filter(grade=grade))
    exams = list(Exam.objects.filter(grade=grade, exam_code__in=exam_codes).select_related("subject"))
    marks = list(Mark.objects.filter(student__in=learners, exam__in=exams))

    exam_dict = {(exam.exam_code, exam.subject.code): exam.id for exam in exams}
    mark_dict = {(mark.student_id, mark.exam_id): mark.score for mark in marks}

    reports = {}

    for learner in learners:
        data = {}

        for ph in placeholders:
            if ph == "NAME":
                data[ph] = learner.name
                continue

            if ph == "GRADE":
                data[ph] = learner.grade.name
                continue

            if ph == "YEAR":
                data[ph] = 2026
                continue

            if "_" not in ph:
                continue

            subject_code, term = ph.split("_")

            if term == "0":
                scores = []

                for exam_code in exam_codes:
                    exam_id = exam_dict.get((exam_code, subject_code))

                    if exam_id:
                        scores.append(
                            mark_dict.get((learner.id, exam_id), 0)
                        )

                data[ph] = round(sum(scores) / len(scores), 2) if scores else ""
                continue

            if term == "1":
                exam_code = exam_codes[0]

            elif term == "2":
                exam_code = exam_codes[1]

            elif term == "3":
                exam_code = exam_codes[2]

            else:
                data[ph] = ""
                continue

            exam_id = exam_dict.get((exam_code, subject_code))

            data[ph] = mark_dict.get((learner.id, exam_id), "") if exam_id else ""

        reports[learner] = data

    return reports


def replace_placeholders(doc, values):
    for paragraph in doc.paragraphs:
        for key, value in values.items():
            placeholder = f"[{key}]"

            if placeholder in paragraph.text:
                for run in paragraph.runs:
                    run.text = run.text.replace(placeholder, str(value))

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for key, value in values.items():
                        placeholder = f"[{key}]"

                        if placeholder in paragraph.text:
                            for run in paragraph.runs:
                                run.text = run.text.replace(placeholder, str(value))


def generate_class_reports(template_path, reports):
    master = Document()

    if master.paragraphs:
        p = master.paragraphs[0]._element
        p.getparent().remove(p)

    for index, values in enumerate(reports.values()):
        doc = Document(template_path)

        replace_placeholders(doc, values)

        for element in doc.element.body:
            master.element.body.append(deepcopy(element))

        if index < len(reports) - 1:
            master.add_page_break()

    buffer = BytesIO()
    master.save(buffer)
    buffer.seek(0)

    return buffer