from cbl_calculator import rollup_to_traditional_grade, \
    calculate_traditional_grade
from canvasapi import Canvas

from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests, json
from datetime import datetime

import itertools
from operator import itemgetter
import time

from pymongo import MongoClient

import asyncio
import aiohttp

access_token = os.getenv('ACCESS_TOKEN')
headers = {'Authorization': f'Bearer {access_token}'}
url = 'https://dtechhs.instructure.com'


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
    response = requests.request("GET", url, headers=headers)

    data = response.json()
    requested_fields = ['id', 'title', 'display_name']
    data_cleaned = {
        '_id': data['id'],
        'title': data['title'],
        'display_name': data['display_name']
    }

    return data_cleaned


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
    client = MongoClient('localhost', 27017)
    db = client.test_database
    outcomes_collection = db.outcomes

    outcome_ids = db.grades.distinct("courses.outcomes.outcome_id")
    print(outcome_ids)
    outcome_ids_in_db = db.outcomes.distinct('_id')
    # check if id is already in database if so, remove it
    print(outcome_ids_in_db)
    new_outcomes = set(outcome_ids) - set(outcome_ids_in_db)
    print(new_outcomes)
    outcomes = [outcome_request(outcome_id) for outcome_id in new_outcomes]

    # If there are any new outcomes, add them to the list
    if len(outcomes):
        outcomes_collection.insert_many(outcomes)


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


def main():
    # Get current term(s) - todo search for all terms within a date. Will return a list if more than one term
    current_term = 10

    # get all active courses
    url = "https://dtechhs.instructure.com/api/v1/accounts/1/courses"
    querystring = {'enrollment_term_id': 10, 'published': True,
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

    # get outcome result rollups for each course - attach to the course dictionary
    outcome_grades = []
    pattern = '@dtech|Innovation Diploma FIT'
    for course in courses:
        if re.search(pattern, course['name']):
            continue
        # Get the outcome_rollups for the current class
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

        # Make the student Objects
        for outcome_rollup in outcome_rollups:
            outcome_grades += append_rollup_details(outcome_rollup, course)

    timestamp = datetime.utcnow()

    # group by student
    data_sorted = sorted(outcome_grades, key=itemgetter('student_id'))
    grouped = itertools.groupby(data_sorted, key=itemgetter('student_id'))
    student_objects = [{'student_id': student_id, 'timestamp': timestamp,
                        'term_id': current_term,
                        'courses': sorted(list(values),
                                          key=itemgetter('course_name'))} for
                       student_id, values in grouped]

    # Load into database
    client = MongoClient('localhost', 27017)
    db = client.test_database
    grades = db.grades
    grades.insert_many(student_objects)


if __name__ == '__main__':
    start = time.time()
    # main()
    get_outcomes()
    end = time.time()
    print(end - start)
