from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from app.models import EnrollmentTerm


# class EnrollmentTermForm(FlaskForm):
#     # term = QuerySelectField(query_factory=lambda: EnrollmentTerm.query.all())
#     term = SelectField('Term', coerce=int)
#     submit = SubmitField('Change Current Term')

# class GradeReportForm(FlaskForm):
#     submit = SubmitField('Download Current Term Grade Report')
