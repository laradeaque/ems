import base64
from datetime import datetime
from io import BytesIO
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from django.db.models import Max
from exams.models import Exam, Mark
from students.models import Learner


def format_mark(val):
    """Formats score values: removes trailing .0 for integers while preserving real decimals."""
    if val is None or val == "":
        return ""
    try:
        num = float(val)
        if num.is_integer():
            return int(num)
        rounded = round(num, 0)
        return int(rounded) if rounded.is_integer() else rounded
    except (ValueError, TypeError):
        return val


def create_progress_chart(labels, scores):
    """Generates a base64 Data URI line chart using dynamic x-axis labels."""
    # Ensure both arrays exist and match in length
    if not labels or not scores or len(labels) != len(scores):
        return ""

    numeric_scores = [0 if s in ("", None) else float(s) for s in scores]

    # Don't draw a chart if the learner has 0 marks across all exams
    if all(s == 0 for s in numeric_scores):
        return ""

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(7.5, 2.4))

    ax.plot(
        labels,
        numeric_scores,
        color="#1976D2",
        linewidth=2.5,
        marker="o",
        markersize=8,
        markerfacecolor="#43A047",
        markeredgecolor="white",
        markeredgewidth=1.5,
    )

    for x, y in zip(labels, numeric_scores):
        ax.text(
            x,
            y + 2,
            str(int(y)),
            ha="center",
            fontsize=9,
            fontweight="bold",
            color="#424242",
        )

    ax.set_title("Assessment Progress", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total Marks")
    ax.set_ylim(0, max(numeric_scores + [100]) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.grid(color="#DDDDDD", linewidth=0.8)
    fig.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)

    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{base64_image}"


def get_latest_grade_exams(grade):
    """Fetches up to 3 latest distinct exams for a grade ordered chronologically."""
    exam_codes_qs = (
        Exam.objects.filter(grade=grade)
        .values("exam_code")
        .annotate(latest=Max("date_taken"))
        .order_by("-latest")[:3]
    )

    codes = [item["exam_code"] for item in reversed(exam_codes_qs)]

    exam_info = []
    for code in codes:
        sample = Exam.objects.filter(grade=grade, exam_code=code).first()
        if sample:
            name = str(sample.code)
            exam_info.append({"code": code, "name": name})

    return exam_info


def lookup_class(grade):
    """Batch lookup fetching dynamic mark tables and charts for all class learners."""
    learners = list(Learner.objects.filter(grade=grade))
    exam_info = get_latest_grade_exams(grade)

    if not exam_info:
        return []

    exam_codes = [e["code"] for e in exam_info]
    exam_labels = [e["name"] for e in exam_info]

    exams = list(
        Exam.objects.filter(
            grade=grade, exam_code__in=exam_codes
        ).select_related("subject")
    )
    marks = list(Mark.objects.filter(student__in=learners, exam__in=exams))

    exam_dict = {
        (exam.exam_code, exam.subject.code): exam.id
        for exam in exams
        if exam.subject
    }
    mark_dict = {(mark.student_id, mark.exam_id): mark.score for mark in marks}
    subjects = sorted(
        {exam.subject for exam in exams if exam.subject},
        key=lambda s: (getattr(s, "priority", 999), s.code),
    )
    timestamp = datetime.now().strftime("%B, %Y")

    class_reports = []
    for learner in learners:
        subject_rows = []

        for subject in subjects:
            scores = []
            raw_scores = []
            for code in exam_codes:
                exam_id = exam_dict.get((code, subject.code))
                raw_score = mark_dict.get((learner.id, exam_id), "") if exam_id else ""
                scores.append(format_mark(raw_score))
                if raw_score not in ("", None):
                    raw_scores.append(float(raw_score))

            avg = round(sum(raw_scores) / len(raw_scores), 2) if raw_scores else ""

            subject_rows.append({
                "name": subject.name,
                "code": subject.code,
                "scores": scores,
                "overall": format_mark(avg),
            })

        term_totals = []
        raw_term_totals = []
        for code in exam_codes:
            total = 0
            has_marks = False
            for subject in subjects:
                exam_id = exam_dict.get((code, subject.code))
                if exam_id and (learner.id, exam_id) in mark_dict:
                    total += float(mark_dict[(learner.id, exam_id)])
                    has_marks = True

            term_totals.append(format_mark(total) if has_marks else "")
            # ALWAYS append to raw_term_totals to keep length aligned with exam_labels
            raw_term_totals.append(total if has_marks else 0)

        raw_valid_totals = [t for t in raw_term_totals if t > 0]
        overall_avg = (
            round(sum(raw_valid_totals) / len(raw_valid_totals), 2)
            if raw_valid_totals
            else ""
        )

        report_data = {
            "NAME": learner.name,
            "GRADE": learner.grade.name,
            "MONTH_DATE": timestamp,
            "exam_headers": exam_labels,
            "subject_rows": subject_rows,
            "totals": term_totals,
            "overall_total": format_mark(overall_avg),
            "PROGRESS_CHART": create_progress_chart(exam_labels, raw_term_totals),
        }

        class_reports.append({
            "learner": learner,
            "values": report_data
        })

    return class_reports


def lookup_learner(learner):
    """Fetches dynamic marks and calculations for a single learner."""
    exam_info = get_latest_grade_exams(learner.grade)
    if not exam_info:
        return {}

    exam_codes = [e["code"] for e in exam_info]
    exam_labels = [e["name"] for e in exam_info]

    exams = list(
        Exam.objects.filter(
            grade=learner.grade, exam_code__in=exam_codes
        ).select_related("subject")
    )
    marks = list(Mark.objects.filter(student=learner, exam__in=exams))

    exam_dict = {
        (exam.exam_code, exam.subject.code): exam.id
        for exam in exams
        if exam.subject
    }
    mark_dict = {mark.exam_id: mark.score for mark in marks}
    subjects = sorted(
        {exam.subject for exam in exams if exam.subject},
        key=lambda s: (getattr(s, "priority", 999), s.code),
    )
    timestamp = datetime.now().strftime("%B, %Y")

    subject_rows = []
    for subject in subjects:
        scores = []
        raw_scores = []
        for code in exam_codes:
            exam_id = exam_dict.get((code, subject.code))
            raw_score = mark_dict.get(exam_id, "") if exam_id else ""
            scores.append(format_mark(raw_score))
            if raw_score not in ("", None):
                raw_scores.append(float(raw_score))

        avg = round(sum(raw_scores) / len(raw_scores), 2) if raw_scores else ""

        subject_rows.append({
            "name": subject.name,
            "code": subject.code,
            "scores": scores,
            "overall": format_mark(avg),
        })

    term_totals = []
    raw_term_totals = []
    for code in exam_codes:
        total = 0
        has_marks = False
        for subject in subjects:
            exam_id = exam_dict.get((code, subject.code))
            if exam_id and exam_id in mark_dict:
                total += float(mark_dict[exam_id])
                has_marks = True

        term_totals.append(format_mark(total) if has_marks else "")
        # ALWAYS append to raw_term_totals to keep length aligned with exam_labels
        raw_term_totals.append(total if has_marks else 0)

    raw_valid_totals = [t for t in raw_term_totals if t > 0]
    overall_avg = (
        round(sum(raw_valid_totals) / len(raw_valid_totals), 2)
        if raw_valid_totals
        else ""
    )

    return {
        "NAME": learner.name,
        "GRADE": learner.grade.name,
        "MONTH_DATE": timestamp,
        "exam_headers": exam_labels,
        "subject_rows": subject_rows,
        "totals": term_totals,
        "overall_total": format_mark(overall_avg),
        "PROGRESS_CHART": create_progress_chart(exam_labels, raw_term_totals),
    }
