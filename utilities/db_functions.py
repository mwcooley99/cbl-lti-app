from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import bindparam

import pandas as pd

from datetime import datetime
import os

from app.config import configuration

from .db_models import Outcomes, OutcomeResults, Courses, Users, Alignments, \
    Records, Grades, CourseUserLink
from .canvas_api import get_users

config = configuration[os.getenv('PULL_CONFIG')]

# Base = automap_base()

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI)
session = Session(engine)


####################################
# Database Functions
####################################
def upsert_users(users):
    '''
    Upserts users into the Users table
    :param users: list of user dictionaries from Canvas API (/api/v1/accounts/:account_id/users)
    :param session: database session
    :return: None
    '''
    keys = ['id', 'name', 'sis_user_id', 'login_id']
    values = [{key: user[key] for key in keys} for user in users]
    insert_stmt = postgresql.insert(Users).values(values)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'name': insert_stmt.excluded.name,
            'sis_user_id': insert_stmt.excluded.sis_user_id,
            'login_id': insert_stmt.excluded.login_id
        }
    )
    session.execute(update_stmt)
    session.commit()



def upsert_courses(courses):
    '''
    Updates courses table
    :param courses: List of courses dictionaries from (/api/v1/accounts/:account_id/courses)
    :param session: DB session
    :return: None
    '''
    keys = ['id', 'name', 'enrollment_term_id']
    values = [{key: course[key] for key in keys} for course in courses]
    insert_stmt = postgresql.insert(Courses).values(values)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'name': insert_stmt.excluded.name,
            'enrollment_term_id': insert_stmt.excluded.enrollment_term_id
        }
    )
    session.execute(update_stmt)
    session.commit()


def upsert_outcomes(outcomes):
    insert_stmt = postgresql.insert(Outcomes).values(outcomes)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'title': insert_stmt.excluded.title,
            'display_name': insert_stmt.excluded.display_name,
            'calculation_int': insert_stmt.excluded.calculation_int
        }
    )
    session.execute(update_stmt)
    session.commit()


def upsert_alignments(alignments):
    insert_stmt = postgresql.insert(Alignments).values(alignments)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'name': insert_stmt.excluded.name,
        }
    )
    session.execute(update_stmt)
    session.commit()


def upsert_outcome_results(outcome_results):
    insert_stmt = postgresql.insert(OutcomeResults).values(outcome_results)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'score': insert_stmt.excluded.score,
            'course_id': insert_stmt.excluded.course_id,
            'user_id': insert_stmt.excluded.user_id,
            'outcome_id': insert_stmt.excluded.outcome_id,
            'alignment_id': insert_stmt.excluded.alignment_id,
            'submitted_or_assessed_at': insert_stmt.excluded.submitted_or_assessed_at,
            'last_updated': insert_stmt.excluded.last_updated,
            'enrollment_term': insert_stmt.excluded.enrollment_term
        }
    )
    session.execute(update_stmt)
    session.commit()


def update_outcome_res_dropped(values):
    stmt = OutcomeResults.update(). \
        where(OutcomeResults.c.id == bindparam('_id')). \
        values({
        'dropped': bindparam('dropped'),

    })
    session.execute(stmt, values)
    session.commit()


def delete_outcome_results(course_id):
    delete_stmt = OutcomeResults.delete().where(
        OutcomeResults.c.course_id == course_id)
    session.execute(delete_stmt)
    session.commit()


def delete_course_students(course_id):
    delete_stmt = CourseUserLink.delete().where(
        CourseUserLink.c.course_id == course_id
    )
    session.execute(delete_stmt)
    session.commit()


def insert_course_students(students):
    session.execute(CourseUserLink.insert().values(students))
    session.commit()


def create_record(current_term):
    '''
    Creates new record
    :param current_term:
    :param session:
    :return: record_id for newly created record
    '''
    timestamp = datetime.utcnow()
    values = {'created_at': timestamp, 'term_id': current_term}

    # Make new record
    session.execute(Records.insert().values(values))
    session.commit()

    # Grab record to use id later
    record = session.query(Records).order_by(desc(Records.c.id)).first()
    return record[0]


def delete_grades_current_term(current_term):
    delete_stmt = delete_stmt = Grades.delete().where(
        Grades.c.course_id == Courses.c.id).where(
        Courses.c.enrollment_term_id == current_term
    )
    session.execute(delete_stmt)
    session.commit()

def insert_grades_to_db(grades_list):
    session.execute(Grades.insert().values(grades_list))
    session.commit()


def query_current_outcome_results(current_term):
    sql = f"""
            SELECT o_res.id as "_id",
                    o_res.user_id AS "links.user", 
                    o_res.score, o.id AS outcome_id, 
                    c.name AS course_name, 
                    c.id AS course_id, 
                    o.title, 
                    o.calculation_int, 
                    o.display_name, 
                    a.name, 
                    o_res.enrollment_term, 
                    o_res.submitted_or_assessed_at
            FROM outcome_results o_res
                LEFT JOIN courses c ON c.id = o_res.course_id
                LEFT JOIN outcomes o ON o.id = o_res.outcome_id
                LEFT JOIN alignments a ON a.id = o_res.alignment_id
            WHERE o_res.score IS NOT NULL 
                 AND  c.enrollment_term_id = {current_term}
            ORDER BY o_res.submitted_or_assessed_at DESC;
        """
    conn = session.connection()
    outcome_results = pd.read_sql(sql, conn)

    return outcome_results


def get_db_courses(current_term=None):
    stmt = Courses.select(Courses.c.enrollment_term_id == current_term)
    conn = session.connection()
    courses = conn.execute(stmt)
    return courses


if __name__ == '__main__':
    delete_outcome_results(343)
