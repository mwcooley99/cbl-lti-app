import json

from flask import Blueprint, render_template

from app.extensions import db

ENROLLMENT_TERM_ID = 11

blueprint = Blueprint('account', __name__, url_prefix='/account',
                      static_folder='../static')


@blueprint.route('/')
def index():
    stmt = db.text('''
        SELECT DISTINCT u.id AS user_id, u.name, u.login_id, cnt.count
        FROM course_user_link cl
            INNER JOIN users u ON cl.user_id = u.id
            LEFT JOIN (
                SELECT g.user_id, count(*)
                FROM grades g
                    INNER JOIN courses c ON c.id = g.course_id
                WHERE g.grade = 'I'
                    AND c.enrollment_term_id = 11
                GROUP BY g.user_id
            ) cnt ON cnt.user_id = cl.user_id
        ORDER BY name;
        ''')

    results = db.session.execute(stmt)
    keys = ['user_id', 'name', 'email', 'incomplete_count']
    incompletes = [dict(zip(keys, res)) for res in results]

    return render_template('account/incomplete_report.html',
                           incompletes=incompletes)

@blueprint.route('student_dashboard/<user_id>')
def student_dashboard(user_id):

