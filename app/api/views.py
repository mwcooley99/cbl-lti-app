import time
import jwt
import os

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

# api key
api_key = os.getenv('DRAGON_TIME_KEY')

blueprint = Blueprint(
    "api", __name__, url_prefix="/api/v1"
)

@blueprint.route("/dragon_time", methods=["GET"])
def dragon_time():
    enrollment_term = get_enrollment_term()
    stmt = db.text(
        """
        SELECT
            u.sis_user_id
            , g.grade
            , c.sis_course_id
        FROM grades g
            JOIN courses c on c.id = g.course_id
            JOIN users u on u.id = g.user_id
        WHERE c.enrollment_term_id = :enrollment_term_id
        ORDER BY g.id
        """
    ).bindparams(enrollment_term_id=enrollment_term.id)

    results = db.session.execute(stmt)
    data = [dict(row) for row in results]
    encoded = jwt.encode({'results': data}, api_key, algorithm="HS256")
    return jsonify(encoded)
