import matplotlib
matplotlib.use("Agg")

from exams.models import Exam, Mark, ExamCode
from students.models import Learner, Grade
from docxcompose.composer import Composer
from docx.enum.text import WD_BREAK
from django.conf import settings
import matplotlib.pyplot as plt
from docx.shared import Inches
from .forms import ReportForm
from datetime import datetime
from copy import deepcopy
from docx import Document
from copy import deepcopy
from pathlib import Path
from io import BytesIO
import re


BASE_DIR = Path(__file__).resolve().parent.parent
PLACEHOLDER_PATTERN = re.compile(
    r"\[([A-Za-z0-9_]+)\]"
)


def get_placeholders(docx_path=""):
    if not docx_path:
        return []

    doc = Document(docx_path)
    placeholders = []

    def extract(text):
        for match in PLACEHOLDER_PATTERN.findall(text):
            if match not in placeholders:
                placeholders.append(match)

    # Normal paragraphs
    for paragraph in doc.paragraphs:
        extract(paragraph.text)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                extract(cell.text)

    if "[PROGRESS_CHART]" in placeholders:
        placeholders.remove("[PROGRESS_CHART]")

    return placeholders


# def lookup(exam_codes, grade, placeholders):
#     learners = list(Learner.objects.filter(grade=grade))
#     exams = list(Exam.objects.filter(grade=grade, exam_code__in=exam_codes).select_related("subject"))
#     marks = list(Mark.objects.filter(student__in=learners, exam__in=exams))
#
#     exam_dict = {(exam.exam_code, exam.subject.code): exam.id for exam in exams}
#     mark_dict = {(mark.student_id, mark.exam_id): mark.score for mark in marks}
#     timestamp = datetime.now().strftime("%B. %Y")
#
#     reports = {}
#
#     for learner in learners:
#         data = {}
#
#         for ph in placeholders:
#             if ph == "NAME":
#                 data[ph] = learner.name
#                 continue
#
#             if ph == "GRADE":
#                 data[ph] = learner.grade.name
#                 continue
#
#             if ph == "MONTH_DATE":
#                 data[ph] = timestamp
#                 continue
#
#             if "_" not in ph:
#                 continue
#
#             subject_code, term = ph.split("_")
#
#             if term == "0":
#                 scores = []
#
#                 for exam_code in exam_codes:
#                     exam_id = exam_dict.get((exam_code, subject_code))
#
#                     if exam_id:
#                         scores.append(
#                             mark_dict.get((learner.id, exam_id), 0)
#                         )
#
#                 data[ph] = round(sum(scores) / len(scores), 2) if scores else ""
#                 continue
#             elif term == "1":
#                 exam_code = exam_codes[0]
#
#             elif term == "2":
#                 exam_code = exam_codes[1]
#
#             elif term == "3":
#                 exam_code = exam_codes[2]
#
#             else:
#                 data[ph] = ""
#                 continue
#
#             exam_id = exam_dict.get((exam_code, subject_code))
#             data[ph] = mark_dict.get((learner.id, exam_id), "") if exam_id else ""
#
#         reports[learner] = data
#
#     return reports


def lookup(exam_codes, grade, placeholders):
    learners = list(Learner.objects.filter(grade=grade))
    exams = Exam.objects.filter(grade=grade, exam_code__in=exam_codes).select_related("subject")
    exams = list(exams)

    marks = Mark.objects.filter(student__in=learners, exam__in=exams)
    marks = list(marks)

    exam_dict = {
        (exam.exam_code, exam.subject.code): exam.id
        for exam in exams
    }
    mark_dict = {
        (mark.student_id, mark.exam_id): mark.score
        for mark in marks
    }

    # All subject codes available for this grade
    subject_codes = sorted({exam.subject.code for exam in exams})
    timestamp = datetime.now().strftime("%B, %Y")

    reports = {}
    for learner in learners:
        data = {}

        for ph in placeholders:
            if ph == "NAME": data[ph] = learner.name; continue
            if ph == "GRADE": data[ph] = learner.grade.name; continue
            if ph == "MONTH_DATE": data[ph] = timestamp; continue
            if "_" not in ph: continue

            prefix, term = ph.split("_")
            if prefix == "TEST":
                if term == "0":
                    totals = []

                    for exam_code in exam_codes:
                        total = 0

                        for subject_code in subject_codes:
                            exam_id = exam_dict.get((exam_code, subject_code))
                            if exam_id:
                                total += mark_dict.get((learner.id, exam_id), 0)

                        totals.append(total)

                    data[ph] = round(sum(totals) / len(totals), 2) if totals else ""
                    continue

                if term == "1": exam_code = exam_codes[0]
                elif term == "2": exam_code = exam_codes[1]
                elif term == "3": exam_code = exam_codes[2]
                else: data[ph] = ""; continue

                total = 0

                for subject_code in subject_codes:
                    exam_id = exam_dict.get((exam_code, subject_code))
                    if exam_id:
                        total += mark_dict.get((learner.id, exam_id), 0)

                data[ph] = total
                continue

            # Subject marks
            subject_code = prefix

            if term == "0":
                scores = []

                for exam_code in exam_codes:
                    exam_id = exam_dict.get((exam_code, subject_code))
                    if exam_id:
                        scores.append(mark_dict.get((learner.id, exam_id), 0))

                data[ph] = round(sum(scores) / len(scores), 2) if scores else ""
                continue

            if term == "1": exam_code = exam_codes[0]
            elif term == "2": exam_code = exam_codes[1]
            elif term == "3": exam_code = exam_codes[2]
            else: data[ph] = ""; continue
            exam_id = exam_dict.get((exam_code, subject_code))
            data[ph] = mark_dict.get((learner.id, exam_id), "") if exam_id else ""

        reports[learner] = data

    return reports

def replace_placeholders(doc, values):
    """
    Replace every placeholder in the document.
    """
    # Normal paragraphs
    for paragraph in doc.paragraphs:
        text = paragraph.text

        for key, value in values.items():
            text = text.replace(f"[{key}]", str(value))

        if text != paragraph.text:
            paragraph.text = text

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:

                    text = paragraph.text

                    for key, value in values.items():
                        text = text.replace(f"[{key}]", str(value))

                    if text != paragraph.text:
                        paragraph.text = text


def generate_class_reports(template_path, reports):
    """
    Generate one document containing all learner reports.
    Each learner starts on a new page.
    """
    composer = None

    for i, values in enumerate(reports.values()):
        # Load a fresh template for each learner
        learner_doc = Document(template_path)

        # Replace placeholders
        replace_chart(learner_doc, values)
        replace_placeholders(learner_doc, values)

        if i == 0:
            # First learner becomes the master document
            composer = Composer(learner_doc)
        else:
            # Insert a page break before the next learner report
            paragraph = composer.doc.add_paragraph()
            paragraph.add_run().add_break(WD_BREAK.PAGE)

            # Append the learner report
            composer.append(learner_doc)

    # Handle empty reports
    if composer is None:
        empty_doc = Document(template_path)
        buffer = BytesIO()
        empty_doc.save(buffer)
        buffer.seek(0)
        return buffer

    buffer = BytesIO()
    composer.save(buffer)
    buffer.seek(0)

    return buffer

def get_template_path(grade):
    if grade.level == "NURSERY":
        return BASE_DIR / "nursery.docx"
    elif grade.level == "LOWER_PRIMARY":
        return BASE_DIR / "lower-primary.docx"
    elif grade.level == "UPPER_PRIMARY":
        return BASE_DIR / "upper-primary.docx"
    elif grade.level == "JUNIOR_SCHOOL":
        return BASE_DIR / "junior-school.docx"
    else:
        return ""

def create_progress_chart(values):
    tests = ["Opener", "Midterm", "Endterm"]

    scores = [
        values.get("TEST_1", 0),
        values.get("TEST_2", 0),
        values.get("TEST_3", 0),
    ]

    # Convert blanks/None to zero
    scores = [0 if s in ("", None) else float(s) for s in scores]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(5.5, 2.0))
    ax.plot(
        tests, scores, color="#1976D2", linewidth=2.5, marker="o",
        markersize=8, markerfacecolor="#43A047", markeredgecolor="white",
        markeredgewidth=1.5
    )

    # Write the values above each point
    for x, y in zip(tests, scores):
        ax.text(
            x, y + 2, str(int(y)), ha="center",
            fontsize=9, fontweight="bold", color="#424242",
        )

    ax.set_title("Assessment Progress", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total Marks")
    ax.set_ylim(0, max(scores + [100]) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(color="#DDDDDD", linewidth=0.8)
    fig.tight_layout()
    image = BytesIO()
    plt.savefig(image, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    image.seek(0)
    return image

from docx.shared import Inches


def replace_chart(doc, values):
    """
    Replace [PROGRESS_CHART] with generated chart image.
    Works inside paragraphs and table cells.
    """

    def add_chart(paragraph):
        chart = create_progress_chart(values)

        # Remove placeholder text but keep paragraph
        for run in paragraph.runs:
            if "[PROGRESS_CHART]" in run.text:
                run.text = run.text.replace(
                    "[PROGRESS_CHART]",
                    ""
                )

        # Add image into same paragraph
        run = paragraph.add_run()
        run.add_picture(
            chart,
            width=Inches(7.5)
        )

    # Normal paragraphs
    for paragraph in doc.paragraphs:
        if "[PROGRESS_CHART]" in paragraph.text:
            add_chart(paragraph)

    # Tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    if "[PROGRESS_CHART]" in paragraph.text:
                        print("SAVED on field")
                        # add_chart(paragraph)
