from flask import Flask, render_template, session, request, Response, jsonify
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.sql import or_

from pylti.flask import lti, LTI
from pylti.common import LTI_SESSION_KEY

import settings
import logging
import json
import os, time
import requests
from itertools import groupby

from cbl_calculator import calculate_traditional_grade

from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)
# # todo - figure out the samesite cookie setting. Getting warning in Chrome
# app.config.update(
#     SESSION_COOKIE_SECURE=True,
#     SESSION_COOKIE_HTTPONLY=True,
#     SESSION_COOKIE_SAMESITE='Lax',
#     PERMANENT_SESSION_LIFETIME=600,
# )

db = SQLAlchemy(app)

from models import Record, OutcomeAverage, Outcome, Course, Grade, User

# csrf = CSRFProtect(app)
# bootstrap = Bootstrap(app)

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
# Helper Functions
# ============================================
def make_course_object(k, g):
    course = dict(
        name=k,
        outcomes=list(g),
    )
    scores = [outcome.outcome_avg for outcome in course['outcomes']]

    return {**course, **calculate_traditional_grade(scores)}


def get_student_outcome_averages(record, user_id):
    return OutcomeAverage.query \
        .filter_by(record_id=record.id, user_id=user_id) \
        .join(OutcomeAverage.course) \
        .order_by(Course.name, OutcomeAverage.outcome_avg.desc()).all()


def get_student_outcome_averages_for_course(record, user_id, course_id):
    return OutcomeAverage.query \
        .filter_by(record_id=record.id, user_id=user_id, course_id=course_id) \
        .join(OutcomeAverage.course) \
        .order_by(Course.name, OutcomeAverage.outcome_avg.desc()).all()


def get_students_in_course(course_id):
    url = f"https://dtechhs.instructure.com/api/v1/courses/{course_id}/users"
    querystring = {"sort": "email", "enrollment_type[]": "student",
                   "per_page": "100"}
    access_token = os.getenv('CANVAS_API_KEY')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    users = response.json()
    # pagination (
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        users += response.json()
    return users


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
    print(session.get(LTI_SESSION_KEY))
    session['u'] = True
    print('u' in session)

    # store some of the user data in the session
    user_id = request.form.get('custom_canvas_user_id')

    print(json.dumps(request.form, indent=2))

    # Check if they are a student
    # TODO - exclude Teachers
    # Check if it's a student (or teacher currently)
    if 'lis_person_sourcedid' in request.form.keys():
        # get most recent record
        record = Record.query.order_by(Record.id.desc()).first()

        grades = Grade.query.filter_by(record_id=record.id,
                                       user_id=user_id).all()
        if grades:
            return render_template('student_dashboard.html', record=record,
                                   students=[grades])

    # Otherwise they must be an observer
    else:
        record = Record.query.order_by(Record.id.desc()).first()
        # Get observees
        url = f"https://dtechhs.test.instructure.com/api/v1/users/{user_id}/observees"
        access_token = os.getenv('CANVAS_API_KEY')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.request("GET", url, headers=headers)

        # TODO - Check that they have a student.
        students = []
        for observee in response.json():
            # Get all student outcome averages from that record
            grades = Grade.query.filter_by(record_id=record.id,
                                           user_id=observee['id']).all()
            # Only add if not empty
            if grades:
                students.append(grades)

        # Only return if there are grades to display
        if students:
            return render_template('student_dashboard.html', record=record,
                                   students=students)

    app.logger.info(json.dumps(request.form, indent=2))

    return "You are not a student of any course"


@app.route('/student_dashboard', methods=['GET'])
def student_dashboard():
    return render_template('student_dashboard.html')


@app.route('/course_navigation', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='instructor', app=app)
def course_navigation(lti=lti):
    course_title = request.form.get('context_title')
    course_id = request.form.get('custom_canvas_course_id')
    record = Record.query.order_by(Record.id.desc()).first()

    users = Grade.query.filter_by(record_id=record.id, course_id=course_id).\
        join(User).order_by(User.name).all()

    if course_title.startswith('@dtech'):
        # Get all students of the class
        # users = get_students_in_course(course_id)


        # Create student objects
        students = []
        for user in users:
            # Get all student outcome averages from that record
            grades = Grade.query.filter_by(record_id=record.id,
                                           user_id=user.user.id).join(Course)\
                .filter(~Course.name.contains('@dtech')).order_by(Course.name).all()

            if grades:
                students.append(grades)
        if students:
            return render_template('student_dashboard.html', record=record,
                                   students=students)

    return "Work in progess"


@app.route('/course')
def course(course_id=357):
    record = Record.query.order_by(Record.id.desc()).first()

    # users = get_students_in_course(course_id)
    oa = OutcomeAverage.query.filter_by(record_id=record.id,
                                        course_id=course_id)

    users = set([outcome.user_id for outcome in oa])
    students = []
    for user in users:
        outcome_averages = get_student_outcome_averages_for_course(record,
                                                                   user,
                                                                   course_id)

        outcomes = make_course_object(course_id, outcome_averages)
        students.append({'student': user, **outcomes})

    print(students[0])

    students = [
        {
            'name': 'John Doe',
            'grade': 'A',
            'min_score': 2.3,
            'threshold': 3.0
        },
        {
            'name': 'Jane Doe',
            'grade': 'B',
            'min_score': 2.3,
            'threshold': 3.0
        },
    ]
    return render_template('course.html', record=record, students=students)


# Home page
@app.route('/', methods=['GET'])
@lti(error=error, request='any', app=app)
def index(lti=lti):
    return render_template('index.html')


@app.route('/data/<user_id>', methods=['GET', 'POST'])
@lti(error=error, request='session', app=app)
def data(user_id, lti=lti):
    print('u' in session)
    print(session.get(LTI_SESSION_KEY))
    print(session['u'])

    url = f'https://dtechhs.test.instructure.com/api/v1/users/{user_id}'
    access_token = os.getenv('CANVAS_API_KEY')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.request("GET", url, headers=headers)
    print(response.json())
    return jsonify(response.json())


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


@app.route("/dashboard/")
@lti(error=error, request='initial', role='any', app=app)
def dashboard():
    return jsonify({'key:': "hello"})


@app.template_filter('strftime')
def datetimeformat(value, format='%m-%d-%Y'):
    return value.strftime(format)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                Course=Course, Record=Record, Grade=Grade, User=User)


if __name__ == '__main__':
    app.run()
