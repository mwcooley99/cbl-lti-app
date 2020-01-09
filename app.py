from flask import Flask, render_template, session, request, Response, \
    url_for, redirect, jsonify

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from pylti.flask import lti

import settings
import logging
import os, json
import requests

from cbl_calculator import calculation_dictionaries
from utilities.canvas_api import get_course_users, get_observees

from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

db = SQLAlchemy(app)
ma = Marshmallow(app)

from models import Record, OutcomeAverage, Outcome, Course, Grade, User, \
    GradeSchema, UserSchema

# ============================================
# Logging
# ============================================

formatter = logging.Formatter(settings.LOG_FORMAT)
handler = RotatingFileHandler(
    settings.LOG_FILE,
    maxBytes=settings.LOG_MAX_BYTES,
    backupCount=settings.LOG_BACKUP_COUNT
)
handler.setLevel(logging.getLevelName(settings.LOG_LEVEL))
handler.setFormatter(formatter)
app.logger.addHandler(handler)


# ============================================
# Utility Functions
# ============================================

def return_error(msg):
    return render_template('error.html', msg=msg)


def error(exception=None):
    app.logger.error("PyLTI error: {}".format(exception))
    return return_error('''Authentication error,
        please refresh and try again. If this error persists,
        please contact support.''')


# ============================================
# Web Views / Routes
# ============================================

# LTI Launch
@app.route('/launch', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='any', app=app)
def launch(lti=lti):
    """
    Returns the launch page
    request.form will contain all the lti params
    """

    # store some of the user data in the session
    session['user_id'] = request.form.get('custom_canvas_user_id')

    # Check if they are a student
    # TODO - exclude Teachers
    # Check if it's a student (or teacher currently)
    if 'lis_person_sourcedid' in request.form.keys():

        session['users'] = User.query.filter(
            User.id == session['user_id']).with_entities(User.id,
                                                         User.name).all()

        return redirect(
            url_for('student_dashboard', user_id=session['user_id']))

    # Otherwise they must be an observer
    else:
        # Get observees
        response = get_observees(session['user_id'])
        session['users'] = [{'id': obs['id'], 'name': obs['name']} for obs in
                            response.json()]
        user_id = session['users'][0]['id']

        return redirect(url_for('student_dashboard', user_id=user_id))


@app.route('/student_dashboard/<user_id>', methods=['GET'])
@lti(error=error, request='session', role='any', app=app)
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

        # Get current Grades
        grades = Grade.query.filter_by(record_id=record.id,
                                       user_id=user_id).join(Course).filter(
            ~Course.name.contains('@dtech')).order_by(Course.name).all()

        # Create dictionary with outcome details
        outcome_details = [grade.__dict__['outcomes'] for grade in grades]

        if grades:
            return render_template('student_dashboard.html', record=record,
                                   students=session['users'], grades=grades,
                                   calculation_dict=calculation_dictionaries,
                                   outcomes=outcome_details)

    return "You currently don't have any grades!"


@app.route('/course_navigation', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='instructor', app=app)
def course_navigation(lti=lti):
    '''
    Authorization for course navigation
    :param lti: pylti
    :return: redirects to course page or adviser page depending on the course type
    '''
    session['dash_type'] = 'course'
    course_title = request.form.get('context_title')
    session['course_id'] = request.form.get('custom_canvas_course_id')

    if course_title.startswith('@dtech'):
        users = get_course_users({'id': session['course_id']})
        format_users(users)
        user = session['users'][0]
        return redirect(url_for('student_dashboard', user_id=user['id']))

    return redirect(url_for('course_dashboard'))


@app.route("/course_dashboard/")
@lti(error=error, request='session', role='instructor', app=app)
def course_dashboard(lti=lti):
    '''
    Dashboard for core content teachers
    :param lti: pylti
    :return: template for a core content teacher
    '''
    record = Record.query.order_by(Record.id.desc()).first()

    # Get course users
    users = get_course_users({'id': session['course_id']})
    format_users(users)

    user_ids = [user['id'] for user in session['users']]

    grades = Grade.query.filter(Grade.user_id.in_(user_ids)) \
        .filter(Grade.record_id == record.id).join(Course) \
        .filter(~Course.name.contains('@dtech')) \
        .filter(Course.id == session['course_id']).join(User).order_by(
        User.name).all()

    return render_template('course_dashboard.html', students=grades,
                           calculation_dict=calculation_dictionaries,
                           record=record)


def format_users(users):
    keys = ['id', 'name']
    users = [dict(zip(keys, (user['id'], user['name']))) for user in users]
    session['users'] = sorted(users, key=lambda x: x['name'])


# Home page
@app.route('/', methods=['GET'])
@lti(error=error, request='any', app=app)
def index(lti=lti):
    return render_template('index.html')


# LTI XML Configuration
@app.route("/xml/", methods=['GET'])
def xml():
    """
    Returns the lti.xml file for the app.
    XML can be built at https://www.eduappcenter.com/
    """
    try:
        return Response(render_template(
            'lti.xml.j2'), mimetype='application/xml'
        )
    except:
        app.logger.error("Error with XML.")
        return return_error('''Error with XML. Please refresh and try again. If this error persists,
            please contact support.''')


@app.template_filter('strftime')
def datetimeformat(value, format='%m-%d-%Y'):
    return value.strftime(format)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                Course=Course, Record=Record, Grade=Grade, User=User,
                UserSchema=UserSchema, GradeSchema=GradeSchema)


if __name__ == '__main__':
    app.run()
