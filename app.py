from flask import Flask, render_template, session, request, Response, \
    url_for, redirect

from flask_restful import Api

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from pylti.flask import lti, LTI

import settings
import itertools
import logging
import time, json

from utilities.cbl_calculator import calculation_dictionaries, CUTOFF_DATE
from utilities.canvas_api import get_course_users, get_observees
from utilities.helpers import safe_round

from logging.handlers import RotatingFileHandler

# TODO add to db
ENROLLMENT_TERM_ID = 11

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)

from models import Record, OutcomeAverage, Course, Grade, User, \
    OutcomeResult, Outcome, Alignment, CourseUserLink, GradeSchema, UserSchema, \
    OutcomeSchema, AlignmentSchema, OutcomeResultSchema

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

        users = User.query.filter(
            User.id == session['user_id']).with_entities(User.id,
                                                         User.name).all()

        # Add user to session
        session["users"] = [dict(zip(['id', 'name'], users[0]))]

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
@lti(error=error, request='session', role='student', app=app)
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
    session['course_id'] = None
    session.modified = True
    session['course_id'] = request.form.get('custom_canvas_course_id')
    if course_title.startswith('@dtech'):
        # Would be better to run this internally
        users = get_course_users({'id': session['course_id']})
        format_users(users)
        user = session['users'][0]
        return redirect(url_for('student_dashboard', user_id=user['id']))

    return redirect(
        url_for('course_dashboard', course_id=session['course_id']))


@app.route("/course_dashboard/<course_id>")
@lti(error=error, request='session', role='instructor', app=app)
def course_dashboard(course_id, lti=lti):
    '''
    Dashboard for core content teachers
    :param lti: pylti
    :return: template for a core content teacher
    '''
    record = Record.query.order_by(Record.id.desc()).first()

    s = time.perf_counter()
    # Get the grades

    grades = Grade.query.join(Grade.user).options(
        db.joinedload(Grade.user, innerjoin=True)
    ).filter(
        Grade.record_id == record.id, Grade.course_id == course_id
    ).order_by(User.name).all()

    # todo - remove me
    session['users'] = [{'id': grade.user_id} for grade in grades]

    # Base query
    base_query = OutcomeResult.query \
        .filter(OutcomeResult.course_id == course_id)

    # Get outcome info
    outcome_ids = base_query.with_entities(
        OutcomeResult.outcome_id).distinct().all()
    if outcome_ids:
        outcome_id_list = list(zip(*outcome_ids))[0]
    else:
        outcome_id_list = []
    outcomes = Outcome.query.filter(Outcome.id.in_(outcome_id_list)).all()

    #
    outcome_results = base_query.filter(
        OutcomeResult.score.isnot(None)
    ).order_by(
        OutcomeResult.user_id, OutcomeResult.outcome_id).all()
    # res_schema = OutcomeResultSchema()
    # alignments = res_schema.dump(outcomes, many=True)

    # Create outcome average dictionaries todo - move to it's own function
    outcome_averages = {}
    for student_id, stu_aligns in itertools.groupby(outcome_results,
                                                    lambda t: t.user_id):
        temp_dict = {}
        for outcome_id, out_aligns in itertools.groupby(stu_aligns, lambda
                x: x.outcome_id):
            aligns = list(out_aligns)
            full_sum = sum([o.score for o in aligns])
            num_of_aligns = len(aligns)
            full_avg = full_sum / num_of_aligns
            temp_dict[outcome_id] = safe_round(full_avg, 2)

            filtered_align = [o.score for o in out_aligns if
                              o.submitted_or_assessed_at < CUTOFF_DATE]
            if len(filtered_align) > 0:
                min_score = min(filtered_align)
                drop_avg = (full_sum - min_score) / (num_of_aligns - 1)
                if drop_avg > full_avg:
                    temp_dict['outcome_id'] = safe_round(drop_avg, 2)

        outcome_averages[student_id] = temp_dict

    return render_template('course_dashboard.html', students=grades,
                           calculation_dict=calculation_dictionaries,
                           record=record,
                           outcomes=outcomes,
                           outcome_averages=outcome_averages)


@app.route("/course_dashboard/<course_id>/user/<user_id>")
@lti(error=error, request='session', role='instructor', app=app)
def course_detail(course_id=357, user_id=384, lti=lti):
    prev_url = request.referrer
    record = Record.query.order_by(Record.id.desc()).first()

    # Get current grade
    grade = Grade.query.filter(Grade.user_id == user_id) \
        .filter(Grade.course_id == course_id) \
        .first()

    outcomes = OutcomeResult.query.options(
        db.joinedload(OutcomeResult.outcome, innerjoin=True)
    ).options(
        db.joinedload(OutcomeResult.alignment, innerjoin=True)
    ).options(
        db.joinedload(OutcomeResult.course, innerjoin=True)
    ).filter(
        OutcomeResult.user_id == user_id, OutcomeResult.score.isnot(None),
        Course.enrollment_term_id == ENROLLMENT_TERM_ID,
        Course.id == OutcomeResult.course_id
    ).order_by(
        OutcomeResult.course_id, OutcomeResult.outcome_id).all()
    print('********')
    print(outcomes)
    res_schema = OutcomeResultSchema()
    alignments = res_schema.dump(outcomes, many=True)

    return render_template('course_detail.html', grade=grade,
                           calculation_dict=calculation_dictionaries,
                           alignments=alignments, prev_url=prev_url)


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
                UserSchema=UserSchema, GradeSchema=GradeSchema,
                Alignment=Alignment, OutcomeResult=OutcomeResult,
                CourseUserLink=CourseUserLink,
                OutcomeSchema=OutcomeSchema,
                OutcomeResultSchema=OutcomeResultSchema,
                AlignmentSchema=AlignmentSchema)


if __name__ == '__main__':
    app.run()
