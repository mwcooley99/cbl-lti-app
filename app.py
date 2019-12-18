from flask import Flask, render_template, session, request, Response, \
    url_for, redirect

from flask_sqlalchemy import SQLAlchemy

from pylti.flask import lti

import settings
import logging
import os, json
import requests

from cbl_calculator import calculation_dictionaries

from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

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
    print(json.dumps(request.form, indent=2))
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
        url = f"https://dtechhs.instructure.com/api/v1/users/{session['user_id']}/observees"
        access_token = os.getenv('CANVAS_API_KEY')
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.request("GET", url, headers=headers)

        session['users'] = [(obs['id'], obs['name']) for obs in
                            response.json()]
        user_id = session['users'][0][0]
        return redirect(url_for('student_dashboard', user_id=user_id))

    # TODO - make a template
    return "You are not a student of any course"


@app.route('/student_dashboard/<user_id>', methods=['GET'])
@lti(error=error, request='session', role='any', app=app)
def student_dashboard(lti=lti, user_id=None):
    record = Record.query.order_by(Record.id.desc()).first()
    if user_id:  # Todo - this probably isn't needed
        # check user is NOT authorized to access this file
        print(json.dumps(request.form, indent=2))
        auth_users_id = [user[0] for user in session['users']]
        if not (int(user_id) in auth_users_id):
            return "You are not authorized to view this users information"

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


@app.route('/course_test')
def course_test():
    record = Record.query.order_by(Record.id.desc()).first()

    user_ids = [524, 656, 678, 653, 670, 557, 720, 595, 662, 447, 466, 573, 393, 302, 560, 461, 621, 672, 204, 476, 463, 554, 298, 401, 438, 593, 523, 829, 613, 651, 539, 380, 617, 535, 437, 381, 731, 428, 636, 366, 496, 645, 669, 570, 620, 512, 481, 506, 534, 488, 404, 499, 234, 316, 451, 540, 266, 661, 528, 611, 210, 420, 567, 334, 399, 414, 646, 336, 494, 391, 491, 575, 384, 533, 530, 167, 475, 458, 432, 508, 441, 623, 665, 435, 564, 717, 169, 536, 233, 389, 634, 550, 387]

    grades = Grade.query.filter(Grade.user_id.in_(user_ids)) \
        .filter(Grade.record_id == record.id).join(Course) \
        .filter(~Course.name.contains('@dtech')) \
        .filter(Course.id == session['course_id']).join(User).order_by(
        User.name).all()

    return render_template('course_dashboard.html', students=grades,
                           calculation_dict=calculation_dictionaries,
                           record=record)


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
    record = Record.query.order_by(Record.id.desc()).first()

    user_ids = [user[0] for user in session['users']]
    print(user_ids)

    grades = Grade.query.filter(Grade.user_id.in_(user_ids)) \
        .filter(Grade.record_id == record.id).join(Course) \
        .filter(~Course.name.contains('@dtech')) \
        .filter(Course.id == session['course_id']).join(User).order_by(
        User.name).all()

    return render_template('course_dashboard.html', students=grades,
                           calculation_dict=calculation_dictionaries,
                           record=record)


@app.template_filter('strftime')
def datetimeformat(value, format='%m-%d-%Y'):
    return value.strftime(format)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                Course=Course, Record=Record, Grade=Grade, User=User)


if __name__ == '__main__':
    app.run()
