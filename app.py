from flask import Flask, render_template, session, request, Response, jsonify
from flask_pymongo import PyMongo
from flask_bootstrap import Bootstrap
import pymongo
# from flask_oauthlib.provider import OAuth1Provider

from pylti.flask import lti
import settings
import logging
import json
import dateutil
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

mongo = PyMongo(app)

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

    app.logger.info(json.dumps(request.form, indent=2))

    user_data = mongo.db.grades.find_one({'student_id': session['user_id']},
                                         sort=[('_id', pymongo.DESCENDING)])
    if user_data:
        for course in user_data['courses']:
            for outcome in course['outcomes']:
                outcome_info = mongo.db.outcomes.find_one(
                    {'_id': outcome['outcome_id']})
                outcome['info'] = outcome_info
            print(outcome['info'])

        return render_template('launch.html', lis_person_name_full=session[
            'lis_person_name_full'], student_object=user_data)


    # if user is student


    return "You are not a student of any course"


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

if __name__ == '__main__':
    app.run()