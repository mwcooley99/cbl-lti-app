import json

import os
import pandas as pd
import requests
from pandas.io.json import json_normalize

from utilities.db_functions import upsert_enrollment_terms

access_token = os.getenv('CANVAS_API_KEY')

headers = {'Authorization': f'Bearer {access_token}'}
url = 'https://dtechhs.instructure.com'


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
        response = requests.request("GET", url, headers=headers)
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
        response = requests.request("GET", url, headers=headers)
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
        response = requests.request("GET", url, headers=headers)

        data = response.json()
        outcome_results += data['outcome_results']
        alignments += data['linked']['alignments']
        outcomes += data['linked']['outcomes']

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

    response = requests.request("GET", url, headers=headers)
    data = response.json()

    outcome_results = json_normalize(data['outcome_results'])
    alignments = json_normalize(data['linked']['alignments'])
    outcomes = json_normalize(data['linked']['outcomes'])

    # Pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers)
        data = response.json()
        outcome_results = pd.concat(
            [outcome_results, json_normalize(data['outcome_results'])])
        alignments = pd.concat(
            [alignments, json_normalize(data['linked']['alignments'])])
        outcomes = pd.concat(
            [outcomes, json_normalize(data['linked']['outcomes'])])

    outcome_results['course_id'] = course['id']
    return outcome_results, alignments, outcomes


# TODO - have this return the whole dictionary not just the ids (deprecated?)
def get_course_users_ids(course):
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
        response = requests.request("GET", url, headers=headers)
        students += [user['id'] for user in response.json()]

    return students


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
    students = response.json()

    # Pagination
    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers)
        students += response.json()

    return students


def get_observees(user_id):
    url = f"https://dtechhs.instructure.com/api/v1/users/{user_id}/observees"
    response = requests.request("GET", url, headers=headers)

    return response


def get_user_courses(user_id):
    url = f"https://dtechhs.instructure.com/api/v1/users/{user_id}/courses"
    querystring = {"enrollment_type[]": "student",
                   "per_page": "100"}
    courses = requests.request("GET", url, headers=headers).json()
    keys = ['id', 'name', 'enrollment_term_id']
    # courses = [{key: course[key] for key in keys} for course in courses]
    return courses


def get_enrollment_terms():
    url = "https://dtechhs.instructure.com/api/v1/accounts/1/terms"
    querystring = {"per_page": "100"}
    response = requests.request("GET", url, headers=headers,
                                params=querystring)

    terms = response.json()['enrollment_terms']

    while response.links.get('next'):
        url = response.links['next']['url']
        response = requests.request("GET", url, headers=headers)
        new_terms = response.json()['enrollment_terms']
        terms += new_terms

    for term in terms:
        del term['grading_period_group_id']

    return terms


if __name__ == '__main__':
    terms = get_enrollment_terms()
    upsert_enrollment_terms(terms)
