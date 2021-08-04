# -*- coding: utf-8 -*-
"""User views."""
from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    url_for,
    request,
    redirect,
)
from pylti.flask import lti

from app.extensions import db
from app.models import (
    Course,
    Record,
    User,
    OutcomeResult,
    OutcomeResultSchema,
    EnrollmentTerm,
)
from app.queries import get_calculation_dictionaries
from utilities.canvas_api import get_observees

from datetime import datetime

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


def return_error(msg):
    return render_template("500.html")


def error(exception=None):
    current_app.logger.error("PyLTI error: {}".format(exception))
    return return_error(
        """Authentication error,
        please refresh and try again. If this error persists,
        please contact support."""
    )


@blueprint.route("/launch", methods=["POST", "GET"])
@lti(error=error, request="initial", role="any", app=current_app)
def launch(lti=lti):
    """
    Returns the launch page
    request.form will contain all the lti params
    """
    # store some of the user data in the session
    session["user_id"] = request.form.get("custom_canvas_user_id")
    user_id = session["user_id"]

    # Check if they are a student
    # TODO - exclude Teachers
    # Check if it's a student (or teacher currently)
    if "lis_person_sourcedid" in request.form.keys():
        users = (
            User.query.filter(User.id == session["user_id"])
            .with_entities(User.id, User.name)
            .all()
        )

        # Add user to session
        session["users"] = [dict(zip(["id", "name"], users[0]))]

        return redirect(url_for("user.student_dashboard", user_id=user_id))

    # Otherwise they must be an observer
    else:
        # Get observees
        response = get_observees(session["user_id"])
        session["users"] = [
            {"id": obs["id"], "name": obs["name"]} for obs in response.json()
        ]
        user_id = session["users"][0]["id"]

        return redirect(url_for("user.student_dashboard", user_id=user_id))


@blueprint.route("/student_dashboard/<user_id>", methods=["GET"])
@lti(error=error, request="session", role="any", app=current_app)
def student_dashboard(lti=lti, user_id=None):
# def student_dashboard(user_id=None):
    """
    Dashboard froms a student view. Used for students, parents and advisors
    :param lti: pylti
    :param user_id: users Canvas ID
    :return: template or error message
    """
    # TODO REMOVE ME - not using records anymore
    record = Record.query.order_by(Record.id.desc()).first()

    # get current term
    current_term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    if current_term.cut_off_date:
        cut_off_date = current_term.cut_off_date
    else:
        cut_off_date = current_term.end_at

    # format as a string
    cut_off_date = cut_off_date.strftime("%Y-%m-%d")
   
    if user_id:  # Todo - this probably isn't needed
        # check user is NOT authorized to access this file
        auth_users_id = [user["id"] for user in session["users"]]
        
        if not (
            int(user_id) in auth_users_id
            or lti.is_role("admin")
            or lti.is_role("instructor")
        ):  # TODO - OR role = 'admin'
            return "You are not authorized to view this users information"
        alignments, grades, user = get_user_dash_data(user_id)

        # calculation dictionaries
        calculation_dictionaries = get_calculation_dictionaries()

        if grades:
            return render_template(
                "users/dashboard.html",
                record=record,
                user=user,
                cut_off_date=cut_off_date,
                students=session["users"],
                grades=grades,
                calculation_dict=calculation_dictionaries,
                alignments=alignments,
                current_term=current_term
            )

    return "You currently don't have any grades!"


def get_user_dash_data(user_id):
    # Get student, which is linked to user-courses relationship table
    user = User.query.filter(User.id == user_id).first()

    current_term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()

    # get student grades
    grades = (
        user.grades.join(Course)
        .filter(Course.enrollment_term_id == current_term.id)
        .all()
    )
    # Get outcome results
    outcomes_stmt = db.text(
        """
        SELECT ores.id AS ores_id,
            ores.score AS ores_score,
            ores.course_id AS ores_course_id,
            ores.user_id AS ores_user_id,
            ores.outcome_id AS ores_outcome_id,
            ores.alignment_id AS ores_alignment_id,
            ores.submitted_or_assessed_at AS ores_submitted_or_assessed_at,
            ores.last_updated AS ores_last_updated,
            ores.enrollment_term AS ores_enrollment_term,
            c.id AS c_id,
            c.name AS c_name,
            c.enrollment_term_id AS c_enrollment_term_id,
            c.sis_course_id AS c_sis_course_id,
            o.id AS o_id,
            o.title AS o_title,
            o.display_name AS o_display_name,
            o.calculation_int AS o_calculation_int,
            a.id AS a_id,
            a.name AS a_name
        FROM outcome_results ores
            JOIN courses c on c.id = ores.course_id
            JOIN outcomes o on o.id = ores.outcome_id
            JOIN alignments a on a.id = ores.alignment_id
        WHERE ores.user_id = :user_id
                AND ores.score IS NOT NULL
                AND c.enrollment_term_id = :current_term
        ORDER BY  ores.course_id, ores.outcome_id;
        """
    )
    outcomes = db.session.execute(outcomes_stmt, dict(user_id=user_id, current_term=current_term.id))
    
    # format outcome results into json format
    alignments = [alignment_dict(a) for a in outcomes]

    return alignments, grades, user


def alignment_dict(ores):
    alignment =  {
        "id": ores["ores_id"],
        "outcome": {
            "id": ores["o_id"],
            "display_name": ores["o_display_name"],
            "title": ores["o_title"]
        },
        "last_updated": datetime.strftime(ores["ores_last_updated"], '%Y-%m-%dT%H:%M:%S%z'),
        "alignment": {
            "id": ores["a_id"],
            "name": ores["a_name"]
        },
        "course": ores["c_id"],
        "score": ores["ores_score"],
        "submitted_or_assessed_at": datetime.strftime(ores["ores_submitted_or_assessed_at"], '%Y-%m-%dT%H:%M:%S%z'),
        "enrollment_term": ores["ores_enrollment_term"],
        "user": ores["ores_user_id"]
    }
    return alignment