from flask import Flask, render_template, session, request, Response, jsonify
# from flask_oauthlib.provider import OAuth1Provider

from pylti.flask import lti
import settings
import logging
import json
from logging.handlers import RotatingFileHandler

from canvasapi import Canvas

from cbl_report_generator import make_student_object



import aiohttp
import asyncio

asyncio.set_event_loop(asyncio.new_event_loop())
loop = asyncio.get_event_loop()

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

# oauth = OAuth1Provider(app)

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

# Canvas api call wrapper
canvas = Canvas(settings.CANVAS_API_URL, settings.CANVAS_API_KEY)


# ============================================
# Utility Functions
# ============================================

def return_error(msg):
    return render_template('error.htm.j2', msg=msg)


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

    # example of getting lti data from the request
    # let's just store it in our session
    # session['lis_person_name_full'] = request.form.get('lis_person_name_full')
    # session['user_id'] = request.form.get('custom_canvas_user_id')

    # user = canvas.get_user(session['user_id'])
    # courses = user.get_courses(enrollment_type='student')
    # pattern = '^@dtech|Innovation Diploma FIT'
    #
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)

    # data = loop.run_until_complete(asyncio.gather(
    #         *(make_student_object(course, user.id) for course in
    #           courses)))
    # print(data)
    # loop.close()
    # Write the lti params to the console
    data=''
    app.logger.info(json.dumps(request.form, indent=2))

    return render_template('launch.html', lis_person_name_full=session[
        'lis_person_name_full'], student_object=data)


# Home page
@app.route('/', methods=['GET'])
def index(lti=lti):
    return render_template('index.htm.j2')


@app.route('/trying', methods=['GET'])
def trying(lti=lti):
    user = canvas.get_user(531)
    courses = user.get_courses(enrollment_type='student')
    pattern = '^@dtech|Innovation Diploma FIT'

    loop = asyncio.new_event_loop();
    asyncio.set_event_loop(loop)

    data = loop.run_until_complete(asyncio.gather(
            *(make_student_object(course, user.id) for course in
              courses)))
    print(data)
    loop.close()
    # Write the lti params to the console
    app.logger.info(json.dumps(request.form, indent=2))
    data =''
    return render_template('launch.html', lis_person_name_full="Jimmy", student_object=data)

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
