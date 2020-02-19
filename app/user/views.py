# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template, current_app, session, url_for, request, redirect
from pylti.flask import lti

from app.models import Outcome, OutcomeAverage, Course, Record, Grade, \
        User, \
        UserSchema, GradeSchema, Alignment, OutcomeResult, CourseUserLink, \
        OutcomeSchema, OutcomeResultSchema, AlignmentSchema

from app.extensions import db, ma

from utilities.canvas_api import get_observees
from utilities.cbl_calculator import calculation_dictionaries

ENROLLMENT_TERM_ID = 11

blueprint = Blueprint("user", __name__, url_prefix="/users", static_folder="../static")


def return_error(msg):
    return render_template('500.html')


def error(exception=None):
    current_app.logger.error("PyLTI error: {}".format(exception))
    return return_error('''Authentication error,
        please refresh and try again. If this error persists,
        please contact support.''')


@blueprint.route('/launch', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='any', app=current_app)
def launch(lti=lti):
    """
    Returns the launch page
    request.form will contain all the lti params
    """
    # store some of the user data in the session
    session['user_id'] = request.form.get('custom_canvas_user_id')
    user_id = session['user_id']

    # Check if they are a student
    # TODO - exclude Teachers
    # Check if it's a student (or teacher currently)
    if 'lis_person_sourcedid' in request.form.keys():

        users = User.query.filter(
            User.id == session['user_id']).with_entities(User.id,
                                                         User.name).all()

        # Add user to session
        session["users"] = [dict(zip(['id', 'name'], users[0]))]

        return redirect(
            url_for('user.student_dashboard', user_id=user_id))

    # Otherwise they must be an observer
    else:
        # Get observees
        response = get_observees(session['user_id'])
        session['users'] = [{'id': obs['id'], 'name': obs['name']} for obs in
                            response.json()]
        user_id = session['users'][0]['id']

        return redirect(url_for('user.student_dashboard', user_id=user_id))

@blueprint.route('/student_dashboard/<user_id>', methods=['GET'])
@lti(error=error, request='session', role='any', app=current_app)
def student_dashboard(lti=lti, user_id=None):
    '''
    Dashboard froms a student view. Used for students, parents and advisors
    :param lti: pylti
    :param user_id: users Canvas ID
    :return: template or error message
    '''
    record = Record.query.order_by(Record.id.desc()).first()

    if user_id:  # Todo - this probably isn't needed
        # check user is NOT authorized to access this file
        auth_users_id = [user['id'] for user in session['users']]
        if not (int(user_id) in auth_users_id):
            return "You are not authorized to view this users information"

        # Get student, which is linked to user-courses relationship table
        user = User.query.filter(User.id == user_id).first()

        # get student grades
        grades = user.grades.join(Course).filter(
            Course.enrollment_term_id == ENROLLMENT_TERM_ID
        ).all()

        # Get outcome results
        outcomes = OutcomeResult.query.options(
            db.joinedload(OutcomeResult.outcome, innerjoin=True)).options(
            db.joinedload(OutcomeResult.alignment, innerjoin=True)).options(
            db.joinedload(OutcomeResult.course, innerjoin=True)
        ).filter(
            OutcomeResult.user_id == user_id, OutcomeResult.score.isnot(None),
            Course.enrollment_term_id == ENROLLMENT_TERM_ID
        ).order_by(
            OutcomeResult.course_id, OutcomeResult.outcome_id).all()

        res_schema = OutcomeResultSchema()
        alignments = res_schema.dump(outcomes, many=True)

        if grades:
            return render_template('student_dashboard.html', record=record,
                                   user=user,
                                   students=session['users'], grades=grades,
                                   calculation_dict=calculation_dictionaries,
                                   alignments=alignments)

    return "You currently don't have any grades!"
