from flask import Flask, render_template, session, request, Response, jsonify
from flask_pymongo import PyMongo
from sqlalchemy.sql import text, bindparam
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import pymongo
# from flask_oauthlib.provider import OAuth1Provider

from pylti.flask import lti, LTI
import settings
import logging
import json
import os
import dateutil
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DEVELOPMENT_DB_URI')

db = SQLAlchemy(app)
# db.metadata.reflect(bind=db.engine)

from models import Record, OutcomeAverage, Outcome, Course

Bootstrap(app)
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
    session['lis_person_name_full'] = request.form.get('lis_person_name_full')
    session['user_id'] = request.form.get('custom_canvas_user_id')

    if lti.is_role(role='student'):
        print("********")
        print(session['user_id'])
        # get most recent record
        record = Record.query.order_by(Record.id.desc()).first()
        print(record.id)
        # Get all student outcome averages from that record
        # Use sql directly. Need to use a connection.

        # query = text('''
        # SELECT *
        #     FROM outcome_averages
        #     WHERE outcome_averages.user_id = :iddata
        #     AND outcome_averages.record_id = :rec_id;
        # ''')
        #
        # data = {'iddata': session['user_id'], 'rec_id': record.id}
        # conn = db.engine.connect()
        # res = conn.execute(query, **data)
        # outcome_averages_list = [{k: v for k, v in row.items()} for row in res]
        # print(outcome_averages_list)
        # for row in res:
        #     print({k: v for k, v in row.items()})
        # print(res)
        join = OutcomeAverage.query.join(Outcome,
                                         OutcomeAverage.outcome_id == Outcome.id)
        join = db.session.query(OutcomeAverage).join(Outcome,
                                                     OutcomeAverage.outcome_id == id)
        results = join.filter(
            OutcomeAverage.user_id == session['user_id']).all()
        print(type(results[0]))

        # results = db.session.query(Outcome_Average).join(Outcome, Outcome_Average.outcome_id == Outcome.id)
        # .add_columns(Outcome.title).filter_by(user_id=session['user_id'],
        # record_id=record.id).all()
        # group by course
        # Calculate grade per course - Could do this in javascript?
        # Format to json for the template
        # Merge outcome averages with outcome table
        # Render template
        # print(f'results: {results[0][0].__dict__}')

        return "Hello world"

    app.logger.info(json.dumps(request.form, indent=2))
    # print(json.dumps(request.form, indent=2))
    session['roles'] = request.form.get('roles')
    print(session['roles'])

    return "You are not a student of any course"


@app.route('/student_dashboard', methods=['GET'])
def student_dashboard():
    print(session['user_id'])

    print(Outcome.query.first())
    return render_template('student_dashboard.html')


# Home page
@app.route('/', methods=['GET'])
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


@app.route("/dashboard/")
# @lti(error=error, request='initial', role='any', app=app)
def dashboard():
    return jsonify({'key:': "hello"})


@app.template_filter('strftime')
def datetimeformat(value, format='%m-%d-%Y'):
    return value.strftime(format)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                Course=Course, Record=Record)


if __name__ == '__main__':
    app.run()
