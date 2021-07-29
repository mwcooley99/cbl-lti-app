import time
import jwt

from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    url_for,
    request,
    redirect,
    jsonify
)
from app.queries import get_calculation_dictionaries, get_enrollment_term
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
    key = "secret"
    enrollment_term = get_enrollment_term()
    stmt = db.text(
        """
        SELECT
            u.id
            , u.login_id
            , g.grade
            , c.name as course_name
        FROM grades g
            JOIN courses c on c.id = g.course_id
            JOIN users u on u.id = g.user_id
        WHERE c.enrollment_term_id = :enrollment_term_id
        ORDER BY g.id
        """
    ).bindparams(enrollment_term_id=enrollment_term.id)
    results = db.session.execute(stmt)
    data = [dict(row) for row in results]
    encoded = jwt.encode({'data': data}, key, algorithm="HS256")
    return jsonify(encoded)
