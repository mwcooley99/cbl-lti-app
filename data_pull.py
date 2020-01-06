from pdf_reports import pug_to_html, write_report, preload_stylesheet

import pandas as pd
from pandas.io.json import json_normalize

import os, re, requests, sys
from datetime import datetime

import time
import json

from config import configuration
from cbl_calculator import calculate_traditional_grade, weighted_avg

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

OutcomeResults = Table('outcome_results', metadata,
                       Column('id', Integer, primary_key=True),
                       Column('score', Float, nullable=False),
                       Column('course_id', Integer, nullable=False),
                       Column('user_id', Integer, nullable=False),
                       Column('outcome_id', Integer, nullable=False),
                       Column('alignment_id', String, nullable=False),
                       Column('submitted_or_assessed_at', DateTime,
                              nullable=False),
                       Column('last_updated', DateTime, nullable=False),
                       Column('enrollment_term', Integer)
                       )

Alignments = Table('alignments', metadata,
                   Column('id', String, primary_key=True),
                   Column('name', String, nullable=False)
                   )

Outcomes = Table('outcomes', metadata,
                 Column('id', Integer, primary_key=True),
                 Column('title', String, nullable=False),
                 Column('display_name', String),
                 Column('calculation_int', Integer, nullable=False)
                 )

metadata.create_all(engine, checkfirst=True)

session = Session(engine)


####################################
# Database Functions
####################################
def upsert_users(users, session):
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
    session = Session(engine)
    users = get_users()
    upsert_users(users, session)


def upsert_courses(courses, session):
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


####################################
# Canvas API Functions
####################################

def get_users():
    '''
    Roll up current Users into a list of dictionaries (Canvas API /api/v1/accounts/:account_id/users)
    :return: List of user dictionaries
    '''
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


def get_courses(current_term):
    '''
    Roll up current Users into a list of dictionaries (Canvas API /api/v1/accounts/:account_id/courses)
    :param current_term: Canvas Term to filter courses
    :return: list of course dictionaries
    '''
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


def get_outcome_results(course, user_ids=None):
    url = f"https://dtechhs.instructure.com/api/v1/courses/{course['id']}/outcome_results"
    querystring = {
        "include[]": ["alignments", "outcomes.alignments", "outcomes"],
        "per_page": "100"}
    if user_ids:
        querystring['user_ids[]'] = user_ids

    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    data = response.json()

    outcome_results = data['outcome_results']
    alignments = data['linked']['alignments']
    outcomes = data['linked']['outcomes']

    # Pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        data = response.json()
        outcome_results += data['outcome_results']
        alignments += data['linked']['alignments']
        outcomes += data['linked']['outcomes']
        break

    return outcome_results, alignments, outcomes


def create_outcome_dataframes(course, user_ids=None):
    '''
    Creates DataFrames of the  outcome results data pulled from Canvas API:
        /api/v1/courses/:course_id/outcome_results
    :param course: course dictionaries
    :param user_ids: Limit User ids mostly for testing
    :return: Dataframes with outcome_results, assignment alignments, and outcome details
    '''
    url = f"https://dtechhs.instructure.com/api/v1/courses/{course['id']}/outcome_results"
    querystring = {
        "include[]": ["alignments", "outcomes.alignments", "outcomes"],
        "per_page": "100"}
    if user_ids:
        querystring['user_ids[]'] = user_ids

    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    data = response.json()

    outcome_results = json_normalize(data['outcome_results'])
    alignments = json_normalize(data['linked']['alignments'])
    outcomes = json_normalize(data['linked']['outcomes'])

    # Pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        data = response.json()
        outcome_results = pd.concat(
            [outcome_results, json_normalize(data['outcome_results'])])
        alignments = pd.concat(
            [alignments, json_normalize(data['linked']['alignments'])])
        outcomes = pd.concat(
            [outcomes, json_normalize(data['linked']['outcomes'])])

    outcome_results['course_id'] = course['id']
    return outcome_results, alignments, outcomes


def get_course_users(course):
    '''
    Gets list of users for a course
    :param course: course dictionary
    :return: user id's for course
    '''
    url = f"https://dtechhs.instructure.com/api/v1/courses/{course['id']}/users"

    querystring = {"enrollment_type[]": "student",
                   "per_page": "100"}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)
    students = [user['id'] for user in response.json()]

    # Pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers,
                                    params=querystring)
        students += [user['id'] for user in response.json()]

    return students


####################################
# Additional Functions
####################################


def make_grade_object(grade, outcome_avgs, record_id, course, user_id):
    '''
    Creates grade dictionary for grades table
    :param grade: Letter Grade
    :param outcome_avgs: List of outcome average info dictionaries
    :param record_id: Current Record ID
    :param course: Course Dictionary
    :param user_id: User ID
    :return: return dictionary formatted for Grades Table
    '''
    # store in a dict
    grade = dict(
        user_id=user_id,
        course_id=course['id'],
        grade=grade['grade'],
        threshold=grade['threshold'],
        min_score=grade['min_score'],
        record_id=record_id,
        outcomes=outcome_avgs
    )

    return grade


def outcome_results_to_df_dict(df):
    return df.to_dict('records')


def make_empty_grade(course, grades_list, record_id, user_id):
    '''
    Create empty grade for non-graded courses
    :param course: course dictionary
    :param grades_list: list to append empty grade to
    :param record_id: record ID
    :param user_id: user_id
    :return: 
    '''
    empty_grade = {'grade': 'n/a', 'threshold': None,
                   'min_score': None}
    grade = make_grade_object(empty_grade, [], record_id, course,
                              user_id)
    grades_list.append(grade)


def preform_grade_pull(current_term=10):
    '''
    Main function to update courses and calculate and insert new grades
    :param current_term: Term to filter courses
    :return: None
    '''
    session = Session(engine)

    # Create a new record
    record = create_record(current_term, session)

    # get all courses for current term
    courses = get_courses(current_term)

    # add courses to database
    upsert_courses(courses, session)

    # get outcome result rollups for each course and list of outcomes
    pattern = 'Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'

    for idx, course in enumerate(courses):
        print(f'{course["name"]} is course {idx + 1} our of {len(courses)}')

        # Check if it's a non-graded course
        if re.match(pattern, course['name']):
            continue

        grades_list = make_grades_list(course, record)

        if len(grades_list):
            session.execute(Grades.insert().values(grades_list))
            session.commit()


def make_outcome_result(outcome_result, course_id):
    temp_dict = {
        'id': outcome_result['id'],
        'score': outcome_result['score'],
        'course_id': course_id,
        'user_id': outcome_result['links']['user'],
        'outcome_id': outcome_result['links']['learning_outcome'],
        'alignment_id': outcome_result['links']['alignment'],
        'submitted_or_assessed_at': outcome_result['submitted_or_assessed_at'],
        # TODO might need to make this into a datetime object
        'last_updated': str(datetime.utcnow())
        # TODO - remove the change to string
    }
    return temp_dict


def format_outcome(outcome):
    temp_dict = {
        'id': outcome['id'],
        'display_name': outcome['display_name'],
        'title': outcome['title'],
        'calculation_int': outcome['calculation_int']
    }

    return temp_dict


def format_alignments(alignment):
    ids = ['id', 'name']
    return {_id: alignment[_id] for _id in ids}


def pull_outcome_results(current_term=10):
    # get all courses for current term
    courses = get_courses(current_term)
    upsert_courses(courses, session)

    # get outcome result rollups for each course and list of outcomes
    pattern = '@dtech|Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'

    for idx, course in enumerate(courses):
        print(f'{course["name"]} is course {idx + 1} our of {len(courses)}')

        # Check if it's a non-graded course
        if re.match(pattern, course['name']):
            print(course['name'])
            continue

        outcome_results, alignments, outcomes = get_outcome_results(course)

        # Format results, removing Null entries
        outcome_results = [make_outcome_result(outcome_result, course['id'])
                           for
                           outcome_result in outcome_results if
                           outcome_result['score']]

        # Format outcomes
        outcomes = [format_outcome(outcome) for outcome in outcomes]
        # Filter out duplicate outcomes
        outcomes = [val for idx, val in enumerate(outcomes) if
                    val not in outcomes[idx + 1:]]

        # format Alignments
        alignments = [format_alignments(alignment) for alignment in alignments]
        # filter out duplicate alignments
        alignments = [val for idx, val in enumerate(alignments) if
                      val not in alignments[idx + 1:]]

        print("hello")
        upsert_outcome_results(outcome_results)
        print("Hello")
        upsert_outcomes(outcomes)
        upsert_alignments(alignments)
        break

        #
        # grades_list = make_grades_list(course, record)
        #
        # if len(grades_list):
        #     session.execute(Grades.insert().values(grades_list))
        #     session.commit()


def make_grades_list(course, record_id):
    '''
    Creates list of student grades for a given course
    :param course: Course dictionary
    :param record_id: Current record ID
    :return:
    '''
    grades_list = []
    students = get_course_users(course)

    for student_num, student in enumerate(students):

        # If @dtech, fill with empty grades - Todo refactor
        if re.match('@dtech', course['name']):
            make_empty_grade(course, grades_list, record_id, student)
            continue

        outcome_results, alignments, outcomes = create_outcome_dataframes(
            course, student)

        # Check if outcome_results are empty. If so make an empty grade object
        if len(outcome_results) == 0:
            make_empty_grade(course, grades_list, record_id, student)
            continue

        # Drop blank scores
        outcome_results = outcome_results.dropna(subset=['score'])

        # Check if outcome_results are empty. If so make an empty grade object
        if len(outcome_results) == 0:
            make_empty_grade(course, grades_list, record_id, student)
            continue

        # Clean up the format of the outcome_results
        outcome_results = format_outcome_results(outcome_results)

        # clean up titles of the outcomes metadata
        outcomes = format_outcomes(outcomes)

        # merge outcome data and create decaying average meta column and alignments
        outcome_results = add_outcome_meta(outcome_results, outcomes,
                                           alignments)

        # Calculate outcome averages using simple and weighted averages
        unfiltered_outcome_averages = calc_outcome_avgs(outcome_results,
                                                        ).round(2)

        # Outcomes with unwanted outcomes filtered out.
        filtered_outcomes = (
            2269, 2270, 2923, 2922, 2732,
            2733)  # TODO - make a constant at the top of script
        filtered_outcome_averages = unfiltered_outcome_averages.loc[
            ~unfiltered_outcome_averages['outcome_id'].isin(
                filtered_outcomes)]

        # Calculate grades
        filtered_grade = calculate_traditional_grade(
            filtered_outcome_averages['outcome_avg'])
        unfiltered_grade = calculate_traditional_grade(
            unfiltered_outcome_averages['outcome_avg'])

        # Pick the higher of the two
        if filtered_grade[1] < unfiltered_grade[1]:
            final_grade = filtered_grade[0]
            final_outcome_avg = filtered_outcome_averages
        else:
            final_grade = unfiltered_grade[0]
            final_outcome_avg = unfiltered_outcome_averages

        # merge the outcome_results with the final outcome_avg
        group_cols = ['outcome_id', 'outcome_avg']

        outcome_results = pd.merge(outcome_results,
                                   final_outcome_avg[group_cols], how='inner',
                                   on='outcome_id',
                                   suffixes=('_results', '_avg'))
        outcome_results = outcome_results.sort_values(
            ['outcome_id', 'submitted_or_assessed_at'], ascending=False)

        group_cols = ['outcome_id', 'outcome_avg', 'title']
        cols = ['name', 'links.alignment', 'score', 'submitted_or_assessed_at']
        outcome_avg_dict = pd.DataFrame(
            outcome_results.groupby(group_cols)[cols].apply(
                lambda x: x.to_dict('records'))).reset_index()

        outcomes_merge = outcomes[['outcome_id', 'display_name']]

        outcome_avg_dict = pd.merge(outcome_avg_dict, outcomes_merge,
                                    how='left', on='outcome_id')

        outcome_avg_dict = outcome_avg_dict.rename(
            columns={0: "alignments"}).sort_values('outcome_avg',
                                                   ascending=False).to_dict(
            'records')

        # create grade object
        grade = make_grade_object(final_grade, outcome_avg_dict, record_id,
                                  course, student)

        grades_list.append(grade)

    return grades_list


def calc_outcome_avgs(outcome_results):
    '''
    Calculates outcome averages with both simple and weighted averages,
    choosing the higher of the two
    :param outcome_results:
    :return: DataFrame of outcome_averages with max of two averages
    '''
    group_cols = ['links.user', 'outcome_id']
    outcome_averages = outcome_results.sort_values(
        ['links.user', 'outcome_id',
         'submitted_or_assessed_at']) \
        .groupby(group_cols).agg(
        {'score': 'mean', 'score_int': weighted_avg})
    outcome_averages = outcome_averages.reset_index()
    outcome_averages['outcome_avg'] = outcome_averages[
        ['score', 'score_int']].max(axis=1).round(2)

    return outcome_averages


def add_outcome_meta(outcome_results, outcomes, alignments):
    '''
    Adds outcome and assignment alignment data to the results dataframe
    :param outcome_results: DataFrame
    :param outcomes: DataFrame
    :param alignments: DataFrame
    :return: DataFrame with outcome and assignments data
    '''
    outcome_results = pd.merge(outcome_results, outcomes, how='left',
                               on='outcome_id')
    outcome_results = pd.merge(outcome_results, alignments[['id', 'name']],
                               how='left', left_on='links.alignment',
                               right_on='id')
    outcome_results['score_int'] = list(
        zip(outcome_results['score'],
            outcome_results['calculation_int'],
            outcome_results['outcome_id']))
    return outcome_results


def format_outcomes(outcomes):
    '''
    Cleans up formatting of outcomes DataFrame
    :param outcomes: outcomes DataFrame
    :return: Reformatted outcomes DataFrame
    '''
    outcomes['id'] = outcomes['id'].astype('int')
    outcomes = outcomes.rename(columns={'id': 'outcome_id'})
    return outcomes


def format_outcome_results(outcome_results):
    '''
    Cleans up formattin of outcome_results DataFrame
    :param outcome_results: outcome_results DataFrame
    :return: Reformatted outcomes DataFrame
    '''
    new_col_names = {'links.learning_outcome': 'outcome_id'}
    outcome_results = outcome_results.rename(columns=new_col_names)
    outcome_results['outcome_id'] = outcome_results[
        'outcome_id'].astype('int')
    outcome_results = outcome_results.sort_values(['links.user', 'outcome_id',
                                                   'submitted_or_assessed_at'])

    return outcome_results


if __name__ == '__main__':
    start = time.time()

    # update_users()
    # preform_grade_pull()
    pull_outcome_results()

    end = time.time()
    print(f'pull took: {end - start} seconds')
