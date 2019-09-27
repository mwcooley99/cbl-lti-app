from cbl_calculator import rollup_to_traditional_grade, \
    calculate_traditional_grade
from canvasapi import Canvas

from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests, json
from datetime import datetime
import pytz
import itertools
from operator import itemgetter
import time
import pymongo
from pymongo import MongoClient


import aiohttp, asyncio

import settings

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


async def make_student_object(course, student_id):
    api = f'https://dtechhs.instructure.com/api/v1/courses/{course.id}/outcome_rollups'
    params = {'user_ids[]': student_id, 'include[]': 'outcomes',
              "per_page": 10}

    access_token = os.getenv('ACCESS_TOKEN')
    headers = {'Authorization': f'Bearer {access_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers, params=params) as resp:
            rollup_response = await resp.json()

    rollups = rollup_response['rollups'][0]
    outcomes_info = rollup_response['linked']['outcomes']

    # Add outcome name to rollup
    outcomes = []
    for rollup in rollups['scores']:
        if rollup['score'] is not None:
            outcome_info = find_outcome(outcomes_info, int(
                rollup['links']['outcome']))
            outcome = {
                'id': outcome_info['id'],
                'title': outcome_info['title'],
                'outcome_display_name': outcome_info['display_name'],
                'url': outcome_info['url'],
                'outcome_average': rollup['score']
            }
            outcomes.append(outcome)

    # calculate traditional_grade
    scores = [outcome['outcome_average'] for outcome in outcomes]
    # traditional_grade_rollup = rollup_to_traditional_grade(scores)
    traditional_grade_rollup = calculate_traditional_grade(scores)
    course_results = {
        'id': course.id,
        'name': course.name,
        'grade': traditional_grade_rollup['grade'],
        'threshold': traditional_grade_rollup['threshold'],
        'min_score': traditional_grade_rollup['min_score'],
        'outcomes': outcomes
    }

    return course_results


def make_report_for_student(student_id=601, sis_id=False):
    api_url = 'https://dtechhs.instructure.com/'
    access_token = os.getenv('ACCESS_TOKEN')

    canvas = Canvas(api_url, access_token)

    if sis_id:
        student = canvas.get_user(student_id, id_type='sis_user_id')
    else:
        student = canvas.get_user(student_id)

    context = {'student': student.attributes,
               'courses': make_student_object(student),
               'calculation_dictionaries': [
                   {
                       'grade': 'A',
                       'threshold': 3.5,
                       'min_score': 3
                   },
                   {
                       'grade': 'A-',
                       'threshold': 3.5,
                       'min_score': 2.5
                   },
                   {
                       'grade': 'B+',
                       'threshold': 3,
                       'min_score': 2.5
                   },
                   {
                       'grade': 'B',
                       'threshold': 3,
                       'min_score': 2.25
                   },
                   {
                       'grade': 'B-',
                       'threshold': 3,
                       'min_score': 2
                   },
                   {
                       'grade': 'C',
                       'threshold': 2.5,
                       'min_score': 2
                   },
                   {
                       'grade': 'I',
                       'threshold': 0,
                       'min_score': 0
                   }
               ], 'date': datetime.today().strftime('%B %d, %Y')}

    html = make_html(context)

    print(f'printing: {context["student"]}')
    file_path = f'out/{student.sis_user_id}.pdf'
    make_pdf(html, file_path=file_path)

    utc_now = pytz.utc.localize(datetime.utcnow())
    pst_now = utc_now.astimezone(pytz.timezone("America/Los_Angeles"))

    with open('logs.txt', 'a+') as f:
        f.write(
            f"Wrote to: {student.name} at {pst_now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}\n")
    print(f'done printing')
    print()


def make_all_students_one_pdf(student_ids, sis_id=True):
    api_url = 'https://dtechhs.instructure.com/'
    access_token = os.getenv('ACCESS_TOKEN')

    canvas = Canvas(api_url, access_token)
    count = 0
    html = ''
    for student_id in student_ids:
        if sis_id:
            student = canvas.get_user(student_id, id_type='sis_user_id')
        else:
            student = canvas.get_user(student_id)
        context = {'student': student.attributes,
                   'courses': make_student_object(student),
                   'calculation_dictionaries': [
                       {
                           'grade': 'A',
                           'threshold': 3.5,
                           'min_score': 3
                       },
                       {
                           'grade': 'A-',
                           'threshold': 3.5,
                           'min_score': 2.5
                       },
                       {
                           'grade': 'B+',
                           'threshold': 3,
                           'min_score': 2.5
                       },
                       {
                           'grade': 'B',
                           'threshold': 3,
                           'min_score': 2.25
                       },
                       {
                           'grade': 'B-',
                           'threshold': 3,
                           'min_score': 2
                       },
                       {
                           'grade': 'C',
                           'threshold': 2.5,
                           'min_score': 2
                       },
                       {
                           'grade': 'I',
                           'threshold': 0,
                           'min_score': 0
                       }
                   ], 'date': datetime.today().strftime('%B %d, %Y')}

        html += make_html(context)
        html += '<div class="break-after"></div>'
        print(f'Added {student.name}')

        count += 1
        if count > 5:
            break

    make_pdf(html, file_path='out/monster.pdf')


def make_all_student_objects():
    api_url = 'https://dtechhs.instructure.com/'
    access_token = os.getenv('ACCESS_TOKEN')
    canvas = Canvas(api_url, access_token)

    account = canvas.get_account(1)
    users = account.get_users(enrollment_type='StudentEnrollment')

    for user in users[:5]:
        print(user)


def create_grade_rollup(course, outcomes_info, rollups):
    # Add outcome name to rollup
    outcomes = []
    for rollup in rollups['scores']:
        if rollup['score'] is not None:
            outcome_info = find_outcome(outcomes_info, int(
                rollup['links']['outcome']))
            outcome = {
                'outcome_id': outcome_info['id'],
                'title': outcome_info['title'],
                'outcome_display_name': outcome_info['display_name'],
                'url': outcome_info['url'],
                'outcome_info': outcome_info,
                'outcome_average': rollup['score']
            }
            outcomes.append(outcome)

    # calculate traditional_grade
    scores = [outcome['outcome_average'] for outcome in outcomes]
    # traditional_grade_rollup = rollup_to_traditional_grade(scores)
    traditional_grade_rollup = calculate_traditional_grade(scores)
    course_results = {
        'course_id': course['id'],
        'name': course['name'],
        'student_id': rollups['links']['user'],
        'grade': traditional_grade_rollup['grade'],
        'threshold': traditional_grade_rollup['threshold'],
        'min_score': traditional_grade_rollup['min_score'],
        'outcomes': outcomes
    }

    return course_results


def append_rollup_details(data, course):
    rollups = data['rollups']
    outcomes_info = data['linked']['outcomes']

    grade_rollup = [create_grade_rollup(course, outcomes_info, rollup) for
                    rollup in rollups]

    return grade_rollup


def main():
    print()
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
    print(courses)

    # get outcome result rollups for each course - attach to the course dictionary

    outcome_grades = []
    for course in courses:

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

        # Shouldn't need this line
        # course['rollups'] = outcome_rollups

        # Make the student Objects
        for outcome_rollup in outcome_rollups:
            outcome_grades += append_rollup_details(outcome_rollup, course)

    timestamp = datetime.timestamp(datetime.utcnow())
    timestamp = datetime.utcnow()
    # group by student
    data_sorted = sorted(outcome_grades, key=itemgetter('student_id'))
    grouped = itertools.groupby(data_sorted, key=itemgetter('student_id'))
    student_objects = [{'student_id': student_id, 'timestamp': timestamp,
                        'courses': list(values)} for
                       student_id, values in grouped]


    client = MongoClient('localhost', 27017)
    db = client.test_database
    grades = db.grades
    grades.insert_many(student_objects)



if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    print(end - start)
    # make_all_student_objects()
    # api_url = 'https://dtechhs.instructure.com/'
    # access_token = os.getenv('ACCESS_TOKEN')
    # canvas = Canvas(api_url, access_token)
    # account = canvas.get_account(1)
    # user = canvas.get_user(466)
    # courses = user.get_courses(enrollment_type='student')
    # # courses = [course for course in courses if course.enrollment_term_id == 10]
    # pattern = '^@dtech|Innovation Diploma FIT'
    #
    # # # make_report_for_student('student_491', True)
    # for user in account.get_users(enrollment_type='student'):
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #
    #     data = loop.run_until_complete(asyncio.gather(
    #         *(make_student_object(course, user.id) for course in
    #           courses)))
    #     student_object = {
    #         'student_id': user.id,
    #         'courses': data
    #     }
    #     print(student_object)
    #     loop.close()

    # api_url = 'https://dtechhs.instructure.com/'
    # access_token = os.getenv('ACCESS_TOKEN')
    #
    # canvas = Canvas(api_url, access_token)
    # student_id = 821
    # student = canvas.get_user(student_id)
    # print(make_student_object(canvas, student))
