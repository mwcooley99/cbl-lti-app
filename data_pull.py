from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests
from datetime import datetime

import time

from config import configuration
from cbl_calculator import calculate_traditional_grade

access_token = os.getenv('CANVAS_API_KEY')

headers = {'Authorization': f'Bearer {access_token}'}
url = 'https://dtechhs.instructure.com'

# todo - move to it's own folder
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Integer, String, Table, Column, MetaData, \
    ForeignKey, DateTime, Float, JSON, desc
from sqlalchemy.dialects import postgresql

config = configuration[os.getenv('PULL_CONFIG')]

Base = automap_base()

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI)

# reflect the tables
metadata = MetaData()
metadata.bind = engine

Records = Table('records', metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('created_at', DateTime),
                Column('term_id', Integer),
                )

OutcomeAverages = Table('outcome_averages', metadata,
                        # Column('id', Integer, primary_key=True),
                        Column('user_id', Integer),
                        Column('outcome_id', Integer),
                        Column('record_id', Integer, ForeignKey('Records.id')),
                        Column('outcome_avg', Float),
                        Column('course_id', Integer)
                        )

Courses = Table('courses', metadata,
                Column('id', Integer, primary_key=True),
                Column('name', String),
                Column('enrollment_term_id', Integer))

Outcomes = Table('outcomes', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('title', String),
                 Column('display_name', String))

Grades = Table('grades', metadata,
               Column('id', Integer, primary_key=True, autoincrement=True),
               Column('user_id', Integer),
               Column('course_id', Integer),
               Column('grade', String),
               Column('outcomes', JSON),
               Column('record_id', Integer),
               Column('threshold', Float),
               Column('min_score', Float),
               )

Users = Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String),
              Column('sis_user_id', String),
              Column('login_id', String))


def find_outcome(outcomes, outcome_id):
    for outcome in outcomes:
        if outcome['id'] == outcome_id:
            return outcome


def make_html(context, template='templates/cbl_report_template.pug'):
    return pug_to_html(template,
                       **context)


def make_pdf(html, file_path="out/example_report.pdf",
             template='templates/cbl_report_template.pug',
             stylesheets='templates/styles.css'):
    css = preload_stylesheet(stylesheets)

    write_report(html, file_path, extra_stylesheets=[css])


def get_outcome_rollups(course):
    outcome_rollups = []
    url = f"https://dtechhs.instructure.com/api/v1/courses/{course['id']}/outcome_rollups"
    querystring = {"include[]": "outcomes", "per_page": "100"}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    # Pagination
    outcome_rollups.append(response.json())
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        outcome_rollups.append(response.json())

    return outcome_rollups


def extract_outcomes(outcomes):
    '''
    Filtering the data that in need for the Outcomes Table
    :param outcomes: List of outcome dictionaries
    :return: list of tuples in the form ('id', 'title', 'display_name'
    '''
    return [(outcome['id'], outcome['title'], outcome['display_name']) for
            outcome in outcomes]


# todo - deprecated - delete
def upsert_outcomes(outcomes, session):
    keys = ['id', 'title', 'display_name']
    values = [dict(zip(keys, outcome)) for outcome in outcomes]

    insert_stmt = postgresql.insert(Outcomes).values(values)
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'title': insert_stmt.excluded.title,
            'display_name': insert_stmt.excluded.display_name
        }
    )
    session.execute(update_stmt)
    session.commit()


def upsert_users(users, session):
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


def get_users():
    url = "https://dtechhs.instructure.com/api/v1/accounts/1/users"

    querystring = {"enrollment_type": "student", "per_page": "100"}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)

    users = response.json()

    # pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        users += response.json()

    return users


def update_users():
    session = Session(engine)
    users = get_users()
    upsert_users(users, session)


def upsert_courses(courses, session):
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


def create_record(current_term, session):
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


def get_courses(current_term):
    url = "https://dtechhs.instructure.com/api/v1/accounts/1/courses"
    querystring = {'enrollment_term_id': current_term, 'published': True,
                   'per_page': 100}
    # initial request
    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    courses = response.json()

    # pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        courses += response.json()
    return courses


# TODO - deprecated - delete
def add_blank_outcome_average(course, user_id, record_id):
    outcome_avg = dict(
        user_id=int(user_id),
        course_id=int(course['id']),
        outcome_id=-1,
        outcome_avg=-1,
        record_id=record_id
    )

    return outcome_avg


def extract_outcome_avg_data(score, course, outcomes):
    outcome_info = find_outcome(outcomes, int(score['links']['outcome']))

    outcome_avg = dict(
        course_id=int(course['id']),  # todo - probably not needed
        outcome_id=int(score['links']['outcome']),
        outcome_avg=score['score'],
        title=outcome_info['title'],
        display_name=outcome_info['display_name'],
    )

    return outcome_avg


def filter_outcomes_grade_rollup(outcome_averages, include_filter=True):
    outcomes_to_filter = (2269, 2270)
    # filtered_scores
    filtered_outcome_averages = [x for x in outcome_averages if
                                 x['outcome_id'] not in outcomes_to_filter]
    filtered_scores = list(
        map(lambda x: x['outcome_avg'], filtered_outcome_averages))
    # print(filtered_scores)
    try:
        filtered_grade_rollup, filtered_index = calculate_traditional_grade(
            filtered_scores)
    except:
        print(filtered_scores)

    # non-filtered scores
    scores = list(map(lambda x: x['outcome_avg'], outcome_averages))
    grade_rollup, index = calculate_traditional_grade(scores)

    if filtered_index < index and include_filter:
        return filtered_grade_rollup, filtered_outcome_averages

    return grade_rollup, outcome_averages


def extract_outcome_averages(course, outcomes, student_rollup):
    outcome_averages = []
    # Iterate through desc sorted outcome averages to extract data we want
    for rollup in sorted(student_rollup['scores'], key=lambda x: x['score'],
                         reverse=True):
        outcome_averages.append(
            extract_outcome_avg_data(rollup, course, outcomes))
    return outcome_averages


def make_grade_object(student_rollup, course, outcomes, record_id, outcome_filter=True):
    '''

    :param student_rollup: canvas outcome_result_rollup
    :param course: canvas course object
    :param outcomes: canvas outcome objects pulled from outcome_result_rollup
    :param record_id: database record id
    :return: grade dictionary
    '''
    user_id = student_rollup['links']['user']
    outcome_averages = extract_outcome_averages(course, outcomes,
                                                student_rollup)

    # calculate grade using cbl algorithm
    # TODO  - Calculate the scores with and without the success skills
    # scores = list(map(lambda x: x['outcome_avg'], outcome_averages))
    # grade_rollup, index = calculate_traditional_grade(scores)
    grade_rollup, outcome_averages = filter_outcomes_grade_rollup(
        outcome_averages, outcome_filter)

    # store in a dict
    grade = dict(
        user_id=user_id,
        course_id=course['id'],
        grade=grade_rollup['grade'],
        threshold=grade_rollup['threshold'],
        min_score=grade_rollup['min_score'],
        record_id=record_id,
        outcomes=outcome_averages
    )

    return grade


def parse_rollups(course, outcome_rollups, record):
    grades = []

    outcomes = outcome_rollups['linked']['outcomes']

    for student_rollup in outcome_rollups['rollups']:
        grade = make_grade_object(student_rollup, course, outcomes, record)
        grades.append(grade)

    return grades


def preform_grade_pull(current_term=10):
    session = Session(engine)

    # Create a new record
    record = create_record(current_term, session)

    # get all courses for current term
    courses = get_courses(current_term)

    # add courses to database
    upsert_courses(courses, session)

    # get outcome result rollups for each course and list of outcomes
    pattern = 'Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'

    for course in courses:
        print(course['name'])
        # Check if it's a non-graded course
        if re.match(pattern, course['name']):
            continue

        # Get the outcome_rollups for the current class
        outcome_rollups_list = get_outcome_rollups(course)

        # Loop through pages of outcome_rollups and make grades for students
        for outcome_rollups in outcome_rollups_list:
            grades = parse_rollups(course,
                                   outcome_rollups,
                                   record)

            if len(grades):
                start = time.time()
                session.execute(Grades.insert().values(grades))
                session.commit()
                end = time.time()

                print(end - start)
                print('******')
                print()


if __name__ == '__main__':
    start = time.time()

    update_users()
    preform_grade_pull()

    end = time.time()
    print(end - start)
