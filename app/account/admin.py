from flask import session
from flask_admin.contrib.sqla import ModelView

from app.extensions import admin, db
from app.models import EnrollmentTerm, GradeCalculation, Task


class CblModelView(ModelView):
    def is_accessible(self):
        if "role" in session:
            return session["role"] == "Admin"
        return True

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return "You're not supposed to be here."


class EnrollmentTermView(CblModelView):
    can_create = False
    can_delete = False
    column_list = ("name", "current_term", "sync_term", "cut_off_date")
    column_editable_list = ["current_term", "sync_term", "cut_off_date"]

    form_excluded_columns = [
        "id",
        "name",
        "start_at",
        "end_at",
        "created_at",
        "workflow_state",
        "sis_term_id",
        "sis_import_id",
    ]

    column_descriptions = dict(
        sync_term=(
            "If true, the nightly sync will update the terms courses, outcome results, grades, etc. "
            "Only select columns that need to be synced for performance. Multiple terms can be selected"
        ),
        current_term="The term that will be displayed in the student/observer view. ONLY ONE can be selected at a time.",
    )


class GradeCriteriaView(CblModelView):
    column_descriptions = dict(
        grade_rank="1 = Highest grade. This order must be correct for grades to calculate correctly"
    )

class TaskView(CblModelView):
    column_editable_list = ["complete"]
    column_descriptions = dict(
        complete = "If a job is clearly dead, but isn't showing as complete (i.e. It's been running for over 4 hours). Change this to `true` to allow a new job."
    )


admin.add_view(EnrollmentTermView(EnrollmentTerm, db.session))
admin.add_view(GradeCriteriaView(GradeCalculation, db.session))
admin.add_view(TaskView(Task, db.session))
