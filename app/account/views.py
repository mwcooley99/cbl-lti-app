from flask import (
    Blueprint,
    render_template,
    current_app,
    session,
    url_for,
    request,
    redirect,
    make_response,
)

import pandas as pd

from pylti.flask import lti

from app.extensions import db
from app.models import Record, EnrollmentTerm, Task
from app.queries import get_calculation_dictionaries, get_enrollment_term
from app.user.views import get_user_dash_data
from utilities.canvas_api import get_course_users
from cron import run
from utilities.helpers import format_users, error
from app.task_utils import launch_task
from rq import get_current_job
from app.account import blueprint

from app.app import create_app

app = create_app()
app.app_context().push()

@blueprint.route("/launch", methods=["POST", "GET"])
@lti(error=error, request="initial", role="admin", app=app)
def launch(lti=lti):
    """
    Authorization for course navigation
    :param lti: pylti
    :return: redirects to course page or adviser page depending on the course type
    """
    # todo - clean up this view
    session["dash_type"] = "course"
    session["role"] = "Admin"
    # session['role'] = 'Teacher'

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

    return redirect(url_for("account.incompletes"))


@blueprint.route("/incompletes")
@lti(error=error, request="session", role="admin", app=app)
def incompletes(lti=lti):
    enrollment_term = get_enrollment_term()
    stmt = db.text(
        """
        SELECT DISTINCT u.id AS user_id, u.name, u.login_id, cnt.count
        FROM course_user_link cl
            INNER JOIN users u ON cl.user_id = u.id
            LEFT JOIN (
                SELECT g.user_id, count(*)
                FROM grades g
                    INNER JOIN courses c ON c.id = g.course_id
                WHERE g.grade = 'I'
                    AND c.enrollment_term_id = :enrollment_term_id
                GROUP BY g.user_id
            ) cnt ON cnt.user_id = cl.user_id
        ORDER BY name;
        """
    ).bindparams(enrollment_term_id=enrollment_term.id)
    results = db.session.execute(stmt)
    keys = ["user_id", "name", "email", "incomplete_count"]
    incompletes = [dict(zip(keys, res)) for res in results]

    return render_template(
        "account/incomplete_report.html",
        incompletes=incompletes,
        enrollment_term_id=enrollment_term.id,
    )


@blueprint.route("student_dashboard/<user_id>")
@lti(error=error, request="session", role="admin", app=app)
def student_dashboard(user_id, lti=lti):
    record = Record.query.order_by(Record.id.desc()).first()
    alignments, grades, user = get_user_dash_data(user_id)

    # get current term
    current_term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    if current_term.cut_off_date:
        cut_off_date = current_term.cut_off_date
    else:
        cut_off_date = current_term.end_at

    # format as a string
    cut_off_date = cut_off_date.strftime("%Y-%m-%d")

    calculation_dictionaries = get_calculation_dictionaries()
    return render_template(
        "account/student_dashboard.html",
        record=record,
        user=user,
        grades=grades,
        cut_off_date=cut_off_date,
        calculation_dict=calculation_dictionaries,
        alignments=alignments,
        prev_url=request.referrer,
        current_term=current_term
    )


@blueprint.route("grade_report", methods=["POST", "GET"])
@lti(error=error, request="session", role="admin", app=app)
def grade_report(lti=lti):
    stmt = """
        SELECT 	u.name student_name,
		right(u.sis_user_id, length(u.sis_user_id) -8) as studentid,
		u.login_id as email,
		c.name as course_name,
		g.grade,
		g.course_id,
		g.threshold,
		g.min_score
    FROM grades g
        LEFT JOIN courses c on c.id = g.course_id
        Left JOIN users u on u.id = g.user_id
        LEFT JOIN enrollment_terms et on et.id = c.enrollment_term_id
    WHERE et.current_term;
    """

    df = pd.read_sql(stmt, db.session.connection())
    resp = make_response(df.to_csv(index=False))
    resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


@blueprint.route("manual_sync", methods=["GET", "POST"])
@lti(error=error, request="session", role="admin", app=app)
def manual_sync(lti=lti):
    task = Task.query.filter(Task.complete == False and Task.name == 'full_sync').first()
    if task is None:
        completed_task = Task.query.filter(Task.complete == True and Task.name == 'full_sync').order_by(Task.completed_at.desc()).first()
    else:
        completed_task = None
    return render_template("account/manual_sync.html", task=task, completed_task=completed_task)


@blueprint.route("run_sync")
@lti(error=error, request="session", role="admin", app=app)
def run_sync(lti=lti):
    # set time limit to 4 hours
    task = launch_task('full_sync', 'running a full sync', job_timeout=14400)
    db.session.commit()

    return redirect(url_for("account.manual_sync"))
