from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql

import pandas as pd

from datetime import datetime
import os

from config import configuration

from .db_models import Outcomes, OutcomeResults, Courses, Users, Alignments, \
    Records, Grades
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


def update_users():
    '''
    Runs through functions to update Users table
    :return: None
    '''
    users = get_users()
    upsert_users(users)


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
        }
    )
    session.execute(update_stmt)
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


def insert_grades_to_db(grades_list):
    session.execute(Grades.insert().values(grades_list))
    session.commit()


def query_current_outcome_results(current_term):
    sql = f"""
            SELECT o_res.user_id AS "links.user", o_res.score, o.id AS outcome_id, 
                    c.name AS course_name, c.id AS course_id, o.title, o.calculation_int, o.display_name, 
                    a.name, o_res.enrollment_term, o_res.submitted_or_assessed_at
            FROM outcome_results o_res
                LEFT JOIN courses c ON c.id = o_res.course_id
                LEFT JOIN outcomes o ON o.id = o_res.outcome_id
                LEFT JOIN alignments a ON a.id = o_res.alignment_id
            WHERE o_res.enrollment_term = {current_term}
            ORDER BY o_res.submitted_or_assessed_at DESC;
        """
    conn = session.connection()
    outcome_results = pd.read_sql(sql, conn)

    return outcome_results