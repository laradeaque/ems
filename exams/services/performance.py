from exams.models import Mark

def get_learner_performance(learner):
    marks = (
        Mark.objects
        .filter(student=learner)
        .select_related("exam")
    )

    performance = {}
    for mark in marks:
        code = mark.exam.exam_code

        if code not in performance:
            performance[code] = {
                "total": 0,
                "count": 0,
                "date_taken": mark.exam.date_taken,
            }

        performance[code]["total"] += mark.score
        performance[code]["count"] += 1


    progress_data = []
    for code, data in performance.items():
        average = data["total"] / data["count"]
        progress_data.append({
            "exam_code": code,
            "average": round(average,2),
            "date_taken": data["date_taken"].isoformat(),
        })

    return sorted(
        progress_data,
        key=lambda x:x["date_taken"]
    )
