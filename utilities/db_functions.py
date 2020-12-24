import os
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, desc
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import bindparam

from app.config import configuration
from utilities.db_models import (
    Outcomes,
    OutcomeResults,
    Courses,
    Users,
    Alignments,
    Records,
    Grades,
    CourseUserLink,
    EnrollmentTerms,
    GradeCalculation,
    CanvasApiToken,
)

def execute_stmt(engine, update_stmt):
    session = Session(engine)
    res = session.execute(update_stmt)
    session.commit()
    session.close()

    return res


####################################
# Database Functions
####################################
def upsert_users(users, engine):
    """
    Upserts users into the Users table
    :param users: list of user dictionaries from Canvas API (/api/v1/accounts/:account_id/users)
    :param session: database session
    :return: None
    """
    keys = ["id", "name", "sis_user_id", "login_id"]
    values = [{key: user[key] for key in keys} for user in users]
    insert_stmt = postgresql.insert(Users).values(values)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": insert_stmt.excluded.name,
            "sis_user_id": insert_stmt.excluded.sis_user_id,
            "login_id": insert_stmt.excluded.login_id,
        },
    )
    execute_stmt(engine, update_stmt)

def upsert_courses(courses, engine):
    """
    Updates courses table
    :param courses: List of courses dictionaries from (/api/v1/accounts/:account_id/courses)
    :param session: DB session
    :return: None
    """
    keys = ["id", "name", "enrollment_term_id"]
    values = [{key: course[key] for key in keys} for course in courses]
    insert_stmt = postgresql.insert(Courses).values(values)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": insert_stmt.excluded.name,
            "enrollment_term_id": insert_stmt.excluded.enrollment_term_id,
        },
    )
    execute_stmt(engine, update_stmt)


def upsert_outcomes(outcomes, engine):
    insert_stmt = postgresql.insert(Outcomes).values(outcomes)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "title": insert_stmt.excluded.title,
            "display_name": insert_stmt.excluded.display_name,
            "calculation_int": insert_stmt.excluded.calculation_int,
        },
    )
    execute_stmt(engine, update_stmt)


def upsert_alignments(alignments, engine):
    insert_stmt = postgresql.insert(Alignments).values(alignments)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"], set_={"name": insert_stmt.excluded.name,}
    )
    execute_stmt(engine, update_stmt)


def upsert_outcome_results(outcome_results, engine):
    insert_stmt = postgresql.insert(OutcomeResults).values(outcome_results)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "score": insert_stmt.excluded.score,
            "course_id": insert_stmt.excluded.course_id,
            "user_id": insert_stmt.excluded.user_id,
            "outcome_id": insert_stmt.excluded.outcome_id,
            "alignment_id": insert_stmt.excluded.alignment_id,
            "submitted_or_assessed_at": insert_stmt.excluded.submitted_or_assessed_at,
            "last_updated": insert_stmt.excluded.last_updated,
            "enrollment_term": insert_stmt.excluded.enrollment_term,
        },
    )
    execute_stmt(engine, update_stmt)


def update_outcome_res_dropped(values):
    stmt = (
        OutcomeResults.update()
        .where(OutcomeResults.c.id == bindparam("_id"))
        .values({"dropped": bindparam("dropped"),})
    )
    session = get_session()
    session.execute(stmt, values)
    session.commit()
    session.close()


def delete_outcome_results(course_id, engine):
    delete_stmt = OutcomeResults.delete().where(OutcomeResults.c.course_id == course_id)
    execute_stmt(engine, delete_stmt)


def delete_course_students(course_id, engine):
    delete_stmt = CourseUserLink.delete().where(CourseUserLink.c.course_id == course_id)
    execute_stmt(engine, delete_stmt)


def insert_course_students(students, engine):
    stmt = CourseUserLink.insert().values(students)
    execute_stmt(engine, stmt)


def create_record(current_term, engine):
    """
    Creates new record
    :param current_term:
    :param session:
    :return: record_id for newly created record
    """
    timestamp = datetime.utcnow()
    values = {"created_at": timestamp, "term_id": current_term}

    # Make new record
    make_stmt = Records.insert().values(values)
    execute_stmt(engine, make_stmt)

    # Grab record to use id later
    session = Session(engine)
    record = session.query(Records).order_by(desc(Records.c.id)).first()
    session.close()
    return record[0]


def delete_grades_current_term(current_term, engine):
    delete_stmt = delete_stmt = (
        Grades.delete()
        .where(Grades.c.course_id == Courses.c.id)
        .where(Courses.c.enrollment_term_id == current_term)
    )
    execute_stmt(engine, delete_stmt)


def insert_grades_to_db(grades_list, engine):
    stmt = Grades.insert().values(grades_list)
    execute_stmt(engine, stmt)


def query_current_outcome_results(current_term, engine):
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
    session = Session(engine)
    conn = session.connection()
    outcome_results = pd.read_sql(sql, conn)
    session.close()

    return outcome_results


def get_db_courses(engine, current_term=None):
    stmt = Courses.select(Courses.c.enrollment_term_id == current_term)
    session = Session(engine)
    conn = session.connection()
    courses = conn.execute(stmt)
    session.close()
    return courses


def upsert_enrollment_terms(enrollment_terms, engine):
    insert_stmt = postgresql.insert(EnrollmentTerms).values(enrollment_terms)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "name": insert_stmt.excluded.name,
            "start_at": insert_stmt.excluded.start_at,
            "end_at": insert_stmt.excluded.end_at,
            "created_at": insert_stmt.excluded.created_at,
            "workflow_state": insert_stmt.excluded.workflow_state,
            "sis_term_id": insert_stmt.excluded.sis_term_id,
            "sis_import_id": insert_stmt.excluded.sis_import_id,
        },
    )
    execute_stmt(engine, update_stmt)


def get_current_term(engine):
    stmt = EnrollmentTerms.select(EnrollmentTerms.c.current_term)
    session = Session(engine)
    conn = session.connection()

    # Get columns for dict conversion
    columns = EnrollmentTerms.c
    columns = [col.key for col in columns]

    # Should only return a single term
    term = list(conn.execute(stmt))[0]
    term = dict(zip(columns, term))

    session.close()

    return term


def get_sync_terms(engine):
    stmt = EnrollmentTerms.select(EnrollmentTerms.c.sync_term)
    session = Session(engine)
    conn = session.connection()

    # Get columns for dict conversion
    columns = EnrollmentTerms.c
    columns = [col.key for col in columns]

    # Can sync multiple terms
    terms = list(conn.execute(stmt))
    terms = [dict(zip(columns, term)) for term in terms]

    session.close()

    return terms


def get_calculation_dictionaries(engine):
    cols = [
        GradeCalculation.c.grade,
        GradeCalculation.c.threshold,
        GradeCalculation.c.min_score,
    ]
    stmt = select(cols).order_by(GradeCalculation.c.grade_rank)

    res = execute_stmt(engine, stmt)

    # Turn into grade dictionaries
    keys = ["grade", "threshold", "min_score"]
    calculation_dictionaries = [dict(zip(keys, r)) for r in res]

    return calculation_dictionaries
    return [r for r in res]


def get_token():
    stmt = select([CanvasApiToken.c.token])
    session = get_session()
    conn = session.connection()
    res = conn.execute(stmt)
    token = [r for r in res]
    
    session = get_session()
    return token[0][0]


if __name__ == "__main__":
    pass