from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests
from datetime import datetime

import time

from config import configuration

access_token = os.getenv('CANVAS_API_KEY')

headers = {'Authorization': f'Bearer {access_token}'}
url = 'https://dtechhs.instructure.com'

# todo - move to it's own folder
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Integer, String, Table, Column, MetaData, \
    ForeignKey, DateTime, Float
from sqlalchemy.dialects import postgresql

config = configuration[os.getenv('PULL_CONFIG')]

Base = automap_base()

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI)

# reflect the tables
Base.prepare(engine, reflect=True)

# mapped classes
Record = Base.classes.records

metadata = MetaData()
metadata.bind = engine

Records = Table('records', metadata,
                # Column('id', Integer, primary_key=True),
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


def extract_outcome_avg_data(score, course, user_id, record_id):
    outcome_avg = dict(
        user_id=int(user_id),
        course_id=int(course['id']),
        outcome_id=int(score['links']['outcome']),
        outcome_avg=score['score'],
        record_id=record_id
    )

    return outcome_avg


def extract_outcomes(outcomes):
    '''
    Filtering the data that in need for the Outcomes Table
    :param outcomes: List of outcome dictionaries
    :return: list of tuples in the form ('id', 'title', 'display_name'
    '''
    return [(outcome['id'], outcome['title'], outcome['display_name']) for
            outcome in outcomes]


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


def add_blank_outcome_average(course, user_id, record_id):
    outcome_avg = dict(
        user_id=int(user_id),
        course_id=int(course['id']),
        outcome_id=-1,
        outcome_avg=-1,
        record_id=record_id
    )

    return outcome_avg


def parse_rollups(course, outcome_averages, outcome_rollups_list, outcomes,
                  record):
    for outcome_rollups in outcome_rollups_list:
        for student_rollup in outcome_rollups['rollups']:
            user_id = student_rollup['links']['user']
            # Check if course has not assessed any outcomes
            if len(student_rollup['scores']) == 0:
                outcome_averages.append(add_blank_outcome_average(course, user_id, record.id))
            else:
                outcome_averages += [
                    extract_outcome_avg_data(score, course, user_id, record.id)
                    for score in student_rollup['scores']]

        # create list of outcomes
        outcomes += extract_outcomes(outcome_rollups['linked']['outcomes'])
        outcomes = list(set(outcomes))
    return outcome_averages, outcomes


def create_record(current_term, session):
    timestamp = datetime.utcnow()
    record = Record(created_at=timestamp, term_id=current_term)
    session.add(record)
    session.commit()
    return record


def main():
    session = Session(engine)
    # Get current term(s) - todo search for all terms within a date. Will return a list if more than one term
    current_term = 10

    # Create a new record
    record = create_record(current_term, session)

    # get all active courses
    courses = get_courses(current_term)

    # add courses to database
    upsert_courses(courses, session)

    # get outcome result rollups for each course and list of outcomes
    outcomes = []
    pattern = '@dtech|Innovation Diploma FIT'
    for course in courses:
        print(course['name'])
        if re.search(pattern, course['name']):
            continue
        # Get the outcome_rollups for the current class
        outcome_rollups_list = get_outcome_rollups(course)

        # Make the student Objects
        outcome_averages = []
        outcome_averages, outcomes = parse_rollups(course, outcome_averages,
                                                   outcome_rollups_list,
                                                   outcomes, record)

        if len(outcome_averages):
            start = time.time()
            session.execute(OutcomeAverages.insert().values(outcome_averages))
            session.commit()
            end = time.time()
            print(end - start)
            print('******')
            print()

    # Add courses to the db
    upsert_outcomes(outcomes, session)


if __name__ == '__main__':
    start = time.time()
    main()
    # get_outcomes()
    end = time.time()
    print(end - start)
