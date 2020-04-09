from flask import session
from flask_admin.contrib.sqla import ModelView

from app.extensions import admin, db
from app.models import EnrollmentTerm, GradeCalculation, CanvasApiToken


class CblModelView(ModelView):
    def is_accessible(self):
        if 'role' in session:
            return session['role'] == 'Admin'
        return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return "You're not supposed to be here."


class EnrollmentTermView(CblModelView):
    can_create = False
    can_delete = False
    column_list = ('name', 'current_term', 'cut_off_date')
    column_editable_list = ['current_term', 'cut_off_date']

    form_excluded_columns = ['id', 'name', 'start_at', 'end_at', 'created_at',
                             'workflow_state', 'sis_term_id', 'sis_import_id']


class GradeCriteriaView(CblModelView):
    column_descriptions = dict(
        grade_rank='1 = Highest grade. This order must be correct for grades to calculate correctly'
    )


class CanvasApiTokenView(CblModelView):
    pass


admin.add_view(EnrollmentTermView(EnrollmentTerm, db.session))
admin.add_view(GradeCriteriaView(GradeCalculation, db.session))
# admin.add_view(CanvasApiTokenView(CanvasApiToken, db.session))
