import time

from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    url_for,
    request,
    redirect,
)

from app.extensions import db
from app.models import (
    Outcome,
    Course,
    Record,
    Grade,
    User,
    OutcomeResult,
    CourseUserLink,
    OutcomeResultSchema,
    OutcomeSchema,
    EnrollmentTerm,
)
from app.queries import get_calculation_dictionaries

from utilities.canvas_api import get_course_users

# from utilities.cbl_calculator import calculation_dictionaries
from utilities.helpers import make_outcome_avg_dicts, format_users, error

blueprint = Blueprint(
    "api", __name__, url_prefix="/api"
)

@blueprint.route("/hello_world")
def hello():
    return "Hello world"

@blueprint.route("/dragon_time", methods=["POST", "GET"])
def dragon_time():
    pass
