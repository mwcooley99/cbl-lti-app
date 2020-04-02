from flask import session
from flask_admin.contrib.sqla import ModelView

from app.extensions import admin, db
from app.models import EnrollmentTerm, GradeCriteria


class CblModelView(ModelView):
    def is_accessible(self):
        if 'role' in session:
            return session['role'] == 'Admin'
        return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return "You're not supposed to be here."


admin.add_view(CblModelView(EnrollmentTerm, db.session))
admin.add_view(CblModelView(GradeCriteria, db.session))
