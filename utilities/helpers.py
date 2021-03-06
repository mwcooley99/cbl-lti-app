import itertools
from flask import render_template, current_app

from utilities.db_functions import get_current_term


def return_error(msg):
    return render_template("500.html", msg=msg)


def error(exception=None):
    current_app.logger.error("PyLTI error: {}".format(exception))
    return return_error(
        """Authentication error,
        please refresh and try again. If this error persists,
        please contact support."""
    )


def safe_round(num, digits):
    if num:
        return round(num, 2)
    else:
        return num


def make_outcome_avg_dicts(outcome_results, grades, current_term):
    outcome_averages = []
    # check if the cut off date has been set
    if current_term.cut_off_date:
        cut_off_date = current_term.cut_off_date
    # if not, set it to the last day of the term
    else:
        cut_off_date = current_term.end_at

    for grade in grades:
        student_dict = {
            "user_name": grade.user.name,
            "user_id": grade.user.id,
            "grade": grade.grade,
            "email": grade.user.login_id,
            "course_id": grade.course_id,
        }
        user_id = grade.user.id
        stu_aligns = list(
            filter(lambda student: student.user_id == user_id, outcome_results)
        )
        for outcome_id, out_aligns in itertools.groupby(
            stu_aligns, lambda x: x.outcome_id
        ):
            aligns = list(out_aligns)
            full_sum = sum([o.score for o in aligns])
            num_of_aligns = len(aligns)
            full_avg = full_sum / num_of_aligns
            temp_avg = {"avg": safe_round(full_avg, 2), "outcome_id": outcome_id}

            filtered_align = [
                o.score for o in out_aligns if o.submitted_or_assessed_at < cut_off_date
            ]
            if len(filtered_align) > 0:
                min_score = min(filtered_align)
                drop_avg = (full_sum - min_score) / (num_of_aligns - 1)
                if drop_avg > full_avg:
                    temp_avg = {
                        "avg": safe_round(drop_avg, 2),
                        "outcome_id": outcome_id,
                    }
            student_dict[str(outcome_id)] = temp_avg["avg"]

        outcome_averages.append(student_dict)

    return outcome_averages


def format_users(users):
    keys = ["id", "name"]
    users = [dict(zip(keys, (user["id"], user["name"]))) for user in users]
    return sorted(users, key=lambda x: x["name"])
