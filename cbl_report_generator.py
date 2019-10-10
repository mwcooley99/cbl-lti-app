from cbl_calculator import rollup_to_traditional_grade, \
    calculate_traditional_grade

from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests
from datetime import datetime

from operator import itemgetter
import time

import asyncio
import aiohttp

from config import configuration

access_token = os.getenv('CANVAS_API_KEY')

headers = {'Authorization': f'Bearer {access_token}'}
url = 'https://dtechhs.instructure.com'

# todo - move to it's own folder
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Integer, String, Table, Column, MetaData, \
    ForeignKey, DateTime
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

config = configuration[os.getenv('CONFIG')]
username = 'TheDoctor'
db_pass = os.getenv('DB_PASSWORD')

Base = automap_base()

engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI)

# reflect the tables
Base.prepare(engine, reflect=True)

# mapped classes
# OutcomeAverage = Base.classes.outcome_averages
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
                        Column('outcome_avg', Integer),
                        Column('course_id', Integer)
                        )

Courses = Table('courses', metadata,
                Column('primary_id', Integer, primary_key=True),
                Column('id', Integer, unique=True),
                Column('name', String),
                Column('enrollment_term_id', Integer))

Outcomes = Table('outcomes', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('title', String),
                 Column('display_name', String))


# Outcome = Base.classes.outcomes


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


def outcome_request(outcome_id):
    url = f"https://dtechhs.instructure.com/api/v1/outcomes/{outcome_id}"
    print(url)
    response = requests.request("GET", url, headers=headers)

    data = response.json()
    print(data)
    data_cleaned = {
        'canvas_id': data['id'],
        'title': data['title'],
        'display_name': data['display_name']
    }

    outcome = Outcome(**data_cleaned)
    return outcome


async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        return await response.json()


async def main_loop(outcome_ids):
    urls = [f"https://dtechhs.instructure.com/api/v1/outcomes/{outcome_id}" for
            outcome_id in outcome_ids]
    tasks = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            tasks.append(fetch(session, url))
        data = await asyncio.gather(*tasks)
        print(data)


def get_outcomes():
    session = Session(engine)
    unique_outcomes = session.query(OutcomeAverage).distinct(
        OutcomeAverage.outcome_id)
    # check if id is already in database if so, remove it

    outcomes = [outcome_request(outcome.outcome_id) for outcome in
                unique_outcomes]

    # todo - want to do more of an upsert
    session.add_all(outcomes)
    session.commit()


def create_grade_rollup(course, outcomes_info, rollups):
    # Add outcome name to rollup
    outcomes = []
    for rollup in rollups['scores']:
        if rollup['score'] is not None:
            outcome_info = find_outcome(outcomes_info, int(
                rollup['links']['outcome']))
            outcome = {
                'outcome_id': outcome_info['id'],
                'outcome_average': rollup['score']
            }
            outcomes.append(outcome)

    # calculate traditional_grade
    scores = [outcome['outcome_average'] for outcome in outcomes]
    # traditional_grade_rollup = rollup_to_traditional_grade(scores)
    traditional_grade_rollup = calculate_traditional_grade(scores)
    course_results = {
        'course_id': course['id'],
        'course_name': course['name'],
        'student_id': rollups['links']['user'],
        'grade': traditional_grade_rollup['grade'],
        'threshold': traditional_grade_rollup['threshold'],
        'min_score': traditional_grade_rollup['min_score'],
        'outcomes': sorted(outcomes, key=itemgetter('outcome_average'),
                           reverse=True)
    }

    return course_results


def append_rollup_details(data, course):
    rollups = data['rollups']
    outcomes_info = data['linked']['outcomes']

    grade_rollup = [create_grade_rollup(course, outcomes_info, rollup) for
                    rollup in rollups]

    return grade_rollup


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
    # outcome_avg = OutcomeAverage(
    #     user_id=user_id,
    #     course_id=course['id'],
    #     outcome_id=score['links']['outcome'],
    #     outcome_avg=score['score'],
    #     record_id=record_id
    # )
    outcome_avg = dict(
        user_id=int(user_id),
        course_id=int(course['id']),
        outcome_id=int(score['links']['outcome']),
        outcome_avg=score['score'],
        record_id=record_id
    )
    course_id = course['id']
    outcome_id = score['links']['outcome']

    return outcome_avg
    # return user_id, course_id, outcome_id, outcome_avg, record_id


def extract_outcomes(outcomes):
    return [(outcome['id'], outcome['title'], outcome['display_name']) for
            outcome in outcomes]


def upsert_outcomes(outcomes, session):
    keys = ['id', 'title', 'display_name']
    values = dict(zip(keys, outcomes))
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


def main():
    session = Session(engine)
    # Get current term(s) - todo search for all terms within a date. Will return a list if more than one term
    current_term = 10

    # Create a new record
    timestamp = datetime.utcnow()
    record = Record(created_at=timestamp, term_id=current_term)
    session.add(record)
    session.commit()

    # get all active courses
    courses = get_courses(current_term)

    # add courses to database
    upsert_courses(courses, session)

    # get outcome result rollups for each course - attach to the course dictionary
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
        for outcome_rollups in outcome_rollups_list:
            for student_rollup in outcome_rollups['rollups']:
                user_id = student_rollup['links']['user']
                outcome_averages += [
                    extract_outcome_avg_data(score, course, user_id, record.id)
                    for score in student_rollup['scores']]

            # create list of outcomes
            outcomes += extract_outcomes(outcome_rollups['linked']['outcomes'])
            outcomes = list(set(outcomes))

        if len(outcome_averages):
            start = time.time()
            session.execute(OutcomeAverages.insert().values(outcome_averages))
            # OutcomeAverage.insert().execute(outcome_averages)
            session.commit()
            end = time.time()
            print(end - start)
            print('******')
            print()

    # Add courses to the db
    upsert_outcomes(outcomes, session)


def get_courses(current_term):
    url = "https://dtechhs.instructure.com/api/v1/accounts/1/courses"
    querystring = {'enrollment_term_id': current_term, 'published': True,
                   'per_page': 100}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    courses = response.json()
    # todo, wrap in a function
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        courses += response.json()
    return courses


if __name__ == '__main__':
    start = time.time()
    main()
    # get_outcomes()
    end = time.time()
    print(end - start)
