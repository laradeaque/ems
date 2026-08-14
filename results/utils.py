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


def get_rubric_info(score):
    """
    Evaluates CBC Rubric code and point weight (1 to 8 scale):
    EE1 = 8, EE2 = 7, ME1 = 6, ME2 = 5, AE1 = 4, AE2 = 3, BE1 = 2, BE2 = 1
    """
    if score is None or score == "":
        return "", 0
    try:
        val = float(score)
    except (ValueError, TypeError):
        return "", 0

    if val >= 90:
        return "EE1", 8
    if val >= 75:
        return "EE2", 7
    if val >= 58:
        return "ME1", 6
    if val >= 41:
        return "ME2", 5
    if val >= 31:
        return "AE1", 4
    if val >= 21:
        return "AE2", 3
    if val >= 11:
        return "BE1", 2
    return "BE2", 1


def format_mark_with_rubric(val):
    """Formats score as 'Mark (Rubric)' e.g., '89 (EE1)' or '8 (BE2)'."""
    formatted = format_mark(val)
    if formatted == "":
        return ""
    code, _ = get_rubric_info(val)
    return f"{formatted} ({code})" if code else str(formatted)


def create_progress_chart(labels, scores):
    """Generates a base64 Data URI line chart using dynamic x-axis labels."""
    if not labels or not scores or len(labels) != len(scores):
        return ""

    numeric_scores = [0 if s in ("", None) else float(s) for s in scores]

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

                scores.append(format_mark_with_rubric(raw_score))

                if raw_score not in ("", None):
                    raw_scores.append(float(raw_score))

            avg = round(sum(raw_scores) / len(raw_scores), 2) if raw_scores else ""

            subject_rows.append({
                "name": subject.name,
                "code": subject.code,
                "scores": scores,
                "raw_avg": avg,
                "overall": format_mark_with_rubric(avg),
            })

        term_totals = []
        raw_term_totals = []
        for code in exam_codes:
            total_marks = 0
            total_pts = 0
            has_marks = False

            for subject in subjects:
                exam_id = exam_dict.get((code, subject.code))
                if exam_id and (learner.id, exam_id) in mark_dict:
                    raw_val = mark_dict[(learner.id, exam_id)]
                    if raw_val not in ("", None):
                        val = float(raw_val)
                        total_marks += val
                        _, pts = get_rubric_info(val)
                        total_pts += pts
                        has_marks = True

            if has_marks:
                term_totals.append(f"{format_mark(total_marks)} ({total_pts})")
                raw_term_totals.append(total_marks)
            else:
                term_totals.append("")
                raw_term_totals.append(0)

        # Overall Average Marks & Points calculation across all subject averages
        valid_subject_avgs = [s["raw_avg"] for s in subject_rows if s["raw_avg"] != ""]
        if valid_subject_avgs:
            overall_total_marks = sum(valid_subject_avgs)
            overall_total_pts = sum(get_rubric_info(avg)[1] for avg in valid_subject_avgs)
            formatted_overall_total = f"{format_mark(overall_total_marks)} ({overall_total_pts})"
        else:
            formatted_overall_total = ""

        report_data = {
            "NAME": learner.name,
            "GRADE": learner.grade.name,
            "MONTH_DATE": timestamp,
            "exam_headers": exam_labels,
            "subject_rows": subject_rows,
            "totals": term_totals,
            "overall_total": formatted_overall_total,
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

            scores.append(format_mark_with_rubric(raw_score))

            if raw_score not in ("", None):
                raw_scores.append(float(raw_score))

        avg = round(sum(raw_scores) / len(raw_scores), 2) if raw_scores else ""

        subject_rows.append({
            "name": subject.name,
            "code": subject.code,
            "scores": scores,
            "raw_avg": avg,
            "overall": format_mark_with_rubric(avg),
        })

    term_totals = []
    raw_term_totals = []
    for code in exam_codes:
        total_marks = 0
        total_pts = 0
        has_marks = False

        for subject in subjects:
            exam_id = exam_dict.get((code, subject.code))
            if exam_id and exam_id in mark_dict:
                raw_val = mark_dict[exam_id]
                if raw_val not in ("", None):
                    val = float(raw_val)
                    total_marks += val
                    _, pts = get_rubric_info(val)
                    total_pts += pts
                    has_marks = True

        if has_marks:
            term_totals.append(f"{format_mark(total_marks)} ({total_pts})")
            raw_term_totals.append(total_marks)
        else:
            term_totals.append("")
            raw_term_totals.append(0)

    # Overall Average Marks & Points calculation across all subject averages
    valid_subject_avgs = [s["raw_avg"] for s in subject_rows if s["raw_avg"] != ""]
    if valid_subject_avgs:
        overall_total_marks = sum(valid_subject_avgs)
        overall_total_pts = sum(get_rubric_info(avg)[1] for avg in valid_subject_avgs)
        formatted_overall_total = f"{format_mark(overall_total_marks)} ({overall_total_pts})"
    else:
        formatted_overall_total = ""

    return {
        "NAME": learner.name,
        "GRADE": learner.grade.name,
        "MONTH_DATE": timestamp,
        "exam_headers": exam_labels,
        "subject_rows": subject_rows,
        "totals": term_totals,
        "overall_total": formatted_overall_total,
        "PROGRESS_CHART": create_progress_chart(exam_labels, raw_term_totals),
    }
