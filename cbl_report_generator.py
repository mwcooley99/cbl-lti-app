from cbl_calculator import rollup_to_traditional_grade
from canvasapi import Canvas

from pdf_reports import pug_to_html, write_report, preload_stylesheet

import os, re, requests
from datetime import datetime
import pytz

import aiohttp, asyncio

import settings


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
              "per_page": 100}

    access_token = os.getenv('ACCESS_TOKEN')
    headers = {'Authorization': f'Bearer {access_token}'}

    async with aiohttp.ClientSession() as session:
        async with session.get(api, headers=headers, params=params) as resp:
            rollup_response = await resp.json()

    rollups = rollup_response['rollups'][0]
    outcomes = rollup_response['linked']['outcomes']

    # Add outcome name to rollup
    outcome_averages = []
    for rollup in rollups['scores']:
        outcome = find_outcome(outcomes, int(
            rollup['links']['outcome']))
        outcome_average = {
            'id': outcome['id'],
            'title': outcome['title'],
            'outcome_display_name': outcome['display_name'],
            'url': outcome['url'],
            'outcome_average': rollup['score']
        }
        outcome_averages.append(outcome_average)


    # calculate traditional_grade
    print(rollups)
    traditional_grade_rollup = rollup_to_traditional_grade(rollups)
    course_results = {
        'id': course.id,
        'name': course.name,
        'grade': traditional_grade_rollup['grade'],
        'threshold': traditional_grade_rollup['threshold'],
        'min_score': traditional_grade_rollup['min_score'],
        'outcome_averages': outcome_averages
    }
    # course_results = {
    #     'rollups': rollups,
    #     'traditional_grade_rollup': traditional_grade_rollup
    # }

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


if __name__ == '__main__':
    api_url = 'https://dtechhs.instructure.com/'
    access_token = os.getenv('ACCESS_TOKEN')
    canvas = Canvas(api_url, access_token)
    user = canvas.get_user(466)
    courses = user.get_courses(enrollment_type='student')
    courses = [course for course in courses if course.enrollment_term_id == 10]
    pattern = '^@dtech|Innovation Diploma FIT'

    # make_report_for_student('student_491', True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    data = loop.run_until_complete(asyncio.gather(
            *(make_student_object(course, user.id) for course in
              courses)))
    print(data)
    loop.close()

    # api_url = 'https://dtechhs.instructure.com/'
    # access_token = os.getenv('ACCESS_TOKEN')
    #
    # canvas = Canvas(api_url, access_token)
    # student_id = 821
    # student = canvas.get_user(student_id)
    # print(make_student_object(canvas, student))
