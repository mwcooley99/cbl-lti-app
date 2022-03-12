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
from pylti.flask import lti

from app.extensions import db
from app.models import (
    Outcome,
    Course,
    Record,
    Grade,
    User,
    OutcomeResult,
    Enrollment,
    OutcomeResultSchema,
    OutcomeSchema,
    EnrollmentTerm,
)
from app.queries import get_calculation_dictionaries

from utilities.canvas_api import get_course_users

# from utilities.cbl_calculator import calculation_dictionaries
from utilities.helpers import make_outcome_avg_dicts, format_users, error

blueprint = Blueprint(
    "course", __name__, url_prefix="/courses", static_folder="../static"
)


@blueprint.route("/launch", methods=["POST", "GET"])
@lti(error=error, request="initial", role="instructor", app=current_app)
def launch(lti=lti):
    """
    Authorization for course navigation
    :param lti: pylti
    :return: redirects to course page or adviser page depending on the course type
    """
    session["dash_type"] = "course"

    course_title = request.form.get("context_title")
    session["course_id"] = None
    session.modified = True
    session["course_id"] = request.form.get("custom_canvas_course_id")
    if course_title.startswith("@dtech"):
        # Would be better to run this internally
        users = get_course_users({"id": session["course_id"]})
        session["users"] = format_users(users)
        user = session["users"][0]
        return redirect(url_for("user.student_dashboard", user_id=user["id"]))

    return redirect(url_for("course.dashboard"))


@blueprint.route("/dashboard")
@lti(error=error, request="session", role="instructor", app=current_app)
def dashboard(lti=lti):
    """
    Dashboard for core content teachers
    :param lti: pylti
    :return: template for a core content teacher
    """
    s = time.perf_counter()
    record = Record.query.order_by(Record.id.desc()).first()
    current_term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    course_id = session["course_id"]

    # Query users
    users = (
        Enrollment.query.join(User)
        .options(db.joinedload(Enrollment.user, innerjoin=True))
        .filter(Enrollment.course_id == course_id)
        .order_by(User.name)
        .all()
    )

    # Query Grades
    grades = (
        Grade.query.join(Grade.user)
        .options(db.joinedload(Grade.user, innerjoin=True))
        .filter(
            # Grade.record_id == record.id,
            Grade.course_id
            == course_id
        )
        .order_by(User.name)
        .all()
    )
    # grade_schema = GradeSchema()
    # grades = grade_schema.dump(grades, many=True)

    # Base query
    base_query = OutcomeResult.query.filter(OutcomeResult.course_id == course_id)

    # Get outcome info
    outcome_ids = base_query.with_entities(OutcomeResult.outcome_id).distinct().all()
    if outcome_ids:
        outcome_id_list = list(zip(*outcome_ids))[0]
    else:
        outcome_id_list = []
    outcomes = Outcome.query.filter(Outcome.id.in_(outcome_id_list)).all()
    outcome_schema = OutcomeSchema()
    outcomes = outcome_schema.dump(outcomes, many=True)

    # Get course outcome_results
    outcome_results = (
        OutcomeResult.query.options(db.joinedload(OutcomeResult.course, innerjoin=True))
        .filter(OutcomeResult.score.isnot(None), OutcomeResult.course_id == course_id)
        .order_by(OutcomeResult.user_id, OutcomeResult.outcome_id)
        .all()
    )
    # res_schema = OutcomeResultSchema()
    # alignments = res_schema.dump(outcome_results, many=True)

    # grade dictionaries
    grades = make_outcome_avg_dicts(outcome_results, grades, current_term)

    calculation_dictionaries = get_calculation_dictionaries()
    return render_template(
        "courses/dashboard.html",
        users=users,
        grades=grades,
        calculation_dict=calculation_dictionaries,
        record=record,
        course_id=course_id,
        outcomes=outcomes,
        # alignments=alignments
    )


@blueprint.route("<course_id>/user/<user_id>")
@lti(error=error, request="session", role="instructor", app=current_app)
def detail(course_id=357, user_id=384, lti=lti):
    prev_url = request.referrer
    record = Record.query.order_by(Record.id.desc()).first()

    # Get user
    user = User.query.filter(User.id == user_id).first()
    # Get course
    course = Course.query.filter(Course.id == course_id).first()

    # get current term
    current_term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    if current_term.cut_off_date:
        cut_off_date = current_term.cut_off_date
    else:
        cut_off_date = current_term.end_at

    # format as a string
    cut_off_date = cut_off_date.strftime("%Y-%m-%d")

    # Get current grade
    grade = (
        Grade.query.filter(Grade.user_id == user_id)
        .filter(Grade.course_id == course_id)
        .first()
    )
    if not grade:
        grade = {"grade": "n/a", "threshold": "n/a", "min_score": "n/a"}

    # Get current outcome results
    outcomes = (
        OutcomeResult.query.options(
            db.joinedload(OutcomeResult.outcome, innerjoin=True)
        )
        .options(db.joinedload(OutcomeResult.alignment, innerjoin=True))
        .options(db.joinedload(OutcomeResult.course, innerjoin=True))
        .filter(
            OutcomeResult.user_id == user_id,
            OutcomeResult.score.isnot(None),
            Course.id == OutcomeResult.course_id,
        )
        .order_by(OutcomeResult.course_id, OutcomeResult.outcome_id)
        .all()
    )

    res_schema = OutcomeResultSchema()
    alignments = res_schema.dump(outcomes, many=True)

    calculation_dictionaries = get_calculation_dictionaries()

    return render_template(
        "courses/detail.html",
        user=user,
        grade=grade,
        course=course,
        cut_off_date=cut_off_date,
        calculation_dict=calculation_dictionaries,
        alignments=alignments,
        prev_url=prev_url,
    )


@blueprint.route("analytics")
@lti(error=error, role="instructor", request="session", app=current_app)
def analytics(course_id=None, lti=lti):
    if not course_id:
        course_id = session["course_id"]
    results = [grade for grade in Course.course_grades(course_id)]
    num_outcomes = (
        OutcomeResult.query.filter(OutcomeResult.course_id == course_id)
        .with_entities(OutcomeResult.outcome_id)
        .distinct()
        .count()
    )
    keys = ["title", "id", "max", "min"]
    outcome_stats = [dict(zip(keys, out)) for out in Course.outcome_stats(course_id)]
    print(outcome_stats)

    graph = [
        {
            "x": [grade[0] for grade in results],
            "y": [grade[1] for grade in results],
            "type": "bar",
        }
    ]

    return render_template(
        "courses/analytics.html", graph=graph, outcome_stats=outcome_stats
    )

