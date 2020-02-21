import time

from flask import Blueprint, render_template, current_app, session, url_for, \
    request, redirect
from pylti.flask import lti

from flask_admin.contrib.pymongo import ModelView

from app.extensions import db, admin
from app.models import Outcome, Course, Record, Grade, User, OutcomeResult, \
    CourseUserLink, OutcomeResultSchema
from utilities.canvas_api import get_course_users
from utilities.cbl_calculator import calculation_dictionaries
from utilities.helpers import make_outcome_avg_dicts, format_users

ENROLLMENT_TERM_ID = 11

blueprint = Blueprint('account', __name__, url_prefix='/account', static_folder='../static')

admin.add_view(ModelView(Outcome, db.session))
