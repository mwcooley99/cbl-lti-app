from flask import Blueprint, render_template, current_app, session, url_for, \
    request, redirect
from pylti.flask import lti

from app.extensions import db
from app.models import Record, EnrollmentTerm
from app.user.views import get_user_dash_data
from app.utils import get_enrollment_term

from utilities.canvas_api import get_course_users
from utilities.cbl_calculator import calculation_dictionaries
from utilities.helpers import format_users, error


from . forms import EnrollmentTermForm




blueprint = Blueprint('account', __name__, url_prefix='/account',
                      static_folder='../static')


@blueprint.route('/launch', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='admin', app=current_app)
def launch(lti=lti):
    '''
    Authorization for course navigation
    :param lti: pylti
    :return: redirects to course page or adviser page depending on the course type
    '''
    # todo - clean up this view
    session['dash_type'] = 'course'

    course_title = request.form.get('context_title')
    session['course_id'] = None
    session.modified = True
    session['course_id'] = request.form.get('custom_canvas_course_id')
    if course_title.startswith('@dtech'):
        # Would be better to run this internally
        users = get_course_users({'id': session['course_id']})
        session['users'] = format_users(users)
        user = session['users'][0]
        return redirect(url_for('user.student_dashboard', user_id=user['id']))

    return redirect(
        url_for('account.incompletes'))


@blueprint.route('/incompletes')
@lti(error=error, request='session', role='admin', app=current_app)
def incompletes(lti=lti):
    enrollment_term_id = get_enrollment_term()
    stmt = db.text('''
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
        ''').bindparams(enrollment_term_id=enrollment_term_id.id)
    results = db.session.execute(stmt)
    keys = ['user_id', 'name', 'email', 'incomplete_count']
    incompletes = [dict(zip(keys, res)) for res in results]

    return render_template('account/incomplete_report.html',
                           incompletes=incompletes)


@blueprint.route('student_dashboard/<user_id>')
@lti(error=error, request='session', role='admin', app=current_app)
def student_dashboard(user_id, lti=lti):
    record = Record.query.order_by(Record.id.desc()).first()
    alignments, grades, user = get_user_dash_data(user_id)
    print(request.referrer)
    return render_template('account/student_dashboard.html', record=record,
                                   user=user,
                                   grades=grades,
                                   calculation_dict=calculation_dictionaries,
                                   alignments=alignments, prev_url=request.referrer)


@blueprint.route('change_term',  methods=['GET', 'POST'])
@lti(error=error, request='session', role='admin', app=current_app)
def change_term(lti=lti):
    form = EnrollmentTermForm()
    terms = EnrollmentTerm.query.all()
    terms_list = [(term.id, term.name) for term in terms]
    form.term.choices = terms_list
    if form.validate_on_submit():
        print(form.term.data)
        return render_template('account/change_term.html', form=form)
    return render_template('account/change_term.html', form=form)
