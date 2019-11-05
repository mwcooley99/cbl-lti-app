from flask import Flask, render_template, session, request, Response, \
    url_for, redirect

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_

from pylti.flask import lti, LTI

import settings
import logging
import json
import os, time
import requests

from cbl_calculator import calculation_dictionaries

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
        url = f"https://dtechhs.test.instructure.com/api/v1/users/{session['user_id']}/observees"
        access_token = os.getenv('CANVAS_API_KEY')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.request("GET", url, headers=headers)

        session['users'] = [(obs['id'], obs['name']) for obs in
                            response.json()]
        user_id = session['users'][0][0]
        return redirect(url_for('student_dashboard', user_id=user_id))

    # TODO - make a template
    return "You are not a student of any course"


@app.route('/student_dashboard', methods=['GET'])
@app.route('/student_dashboard/<user_id>', methods=['GET'])
def student_dashboard(user_id=None):
    record = Record.query.order_by(Record.id.desc()).first()
    if user_id:
        grades = Grade.query.filter_by(record_id=record.id,
                                       user_id=user_id).join(Course) \
            .filter(~Course.name.contains('@dtech')).order_by(
            Course.name).all()

        if grades:
            return render_template('student_dashboard.html', record=record,
                                   students=session['users'], grades=grades,
                                   calculation_dict=calculation_dictionaries)

    return "You currently don't have any grades!"


@app.route('/course_navigation', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='instructor', app=app)
def course_navigation(lti=lti):
    session['dash_type'] = 'course'
    course_title = request.form.get('context_title')
    session['course_id'] = request.form.get('custom_canvas_course_id')
    record = Record.query.order_by(Record.id.desc()).first()

    session['users'] = Grade.query.filter_by(record_id=record.id,
                                             course_id=session['course_id']). \
        join(User).order_by(User.name).with_entities(Grade.user_id,
                                                     User.name).all()

    user = session['users'][0]

    if course_title.startswith('@dtech'):
        return redirect(url_for('student_dashboard', user_id=user[0]))

    return redirect(url_for('course_dashboard'))


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


@app.route("/course_dashboard/")
@lti(error=error, request='session', role='instructor', app=app)
def course_dashboard(lti=lti):
    # Todo - remove after testing
    record = Record.query.order_by(Record.id.desc()).first()
    # session['course_id'] = 357
    # session['users'] = Grade.query.filter_by(record_id=record.id,
    #                                          course_id=session['course_id']). \
    #     join(User).order_by(User.name).with_entities(Grade.user_id,
    #                                                  User.name).all()

    user_ids = [user[0] for user in session['users']]

    # TODO - rewrite to grab all users in user_ids and order by user name
    grades = Grade.query.filter(Grade.user_id.in_(user_ids)) \
        .filter(Grade.record_id == record.id).join(Course) \
        .filter(~Course.name.contains('@dtech')) \
        .filter(Course.id == session['course_id']).join(User).order_by(
        User.name).all()
    print(grades)

    # grades = db.session.query(Grade).filter(record_id=record.id, Grade.user_id.in_(user_ids))

    return render_template('course_dash.html', students=grades,
                           calculation_dict=calculation_dictionaries, record=record)


@app.template_filter('strftime')
def datetimeformat(value, format='%m-%d-%Y'):
    return value.strftime(format)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                Course=Course, Record=Record, Grade=Grade, User=User)


if __name__ == '__main__':
    app.run()
