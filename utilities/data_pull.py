import re
import time
from datetime import datetime

import numpy as np
import pandas as pd

from utilities.canvas_api import get_courses, get_outcome_results, \
    get_course_users, get_users
from utilities.cbl_calculator import calculate_traditional_grade, CUTOFF_DATE
from utilities.db_functions import insert_grades_to_db, create_record, \
    delete_outcome_results, upsert_alignments, upsert_users, \
    upsert_outcome_results, upsert_outcomes, upsert_courses, \
    query_current_outcome_results, get_db_courses, \
    insert_course_students, delete_course_students, delete_grades_current_term

OUTCOMES_TO_FILTER = (
    2269, 2270, 2923, 2922, 2732,
    2733)


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


def make_outcome_result(outcome_result, course_id, enrollment_term):
    temp_dict = {
        'id': outcome_result['id'],
        'score': outcome_result['score'],
        'course_id': course_id,
        'user_id': outcome_result['links']['user'],
        'outcome_id': outcome_result['links']['learning_outcome'],
        'alignment_id': outcome_result['links']['alignment'],
        'submitted_or_assessed_at': outcome_result['submitted_or_assessed_at'],
        'last_updated': datetime.utcnow(),
        # 'enrollment_term': enrollment_term

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
    # get all courses for current term todo move outside of this function
    courses = get_courses(current_term)
    upsert_courses(courses)

    # get outcome result rollups for each course and list of outcomes
    pattern = '@dtech|Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'
    count = 0
    for idx, course in enumerate(courses):
        print(course['id'])
        print(f'{course["name"]} is course {idx + 1} our of {len(courses)}')

        # Check if it's a non-graded course
        if re.match(pattern, course['name']):
            print(course['name'])
            continue

        # get course users
        users = get_course_users(course)
        user_ids = [user['id'] for user in users]

        outcome_results, alignments, outcomes = get_outcome_results(course,
                                                                    user_ids=user_ids)

        # Format results, Removed Null filter (works better for upsert)
        outcome_results = [
            make_outcome_result(outcome_result, course['id'], current_term)
            for
            outcome_result in outcome_results]

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

        # If there are results to upload
        if outcome_results:
            upsert_outcomes(outcomes)
            print('outcome upsert complete')
            upsert_alignments(alignments)
            print('alignment upsert complete')

            print(f'deleting outcome_results for {course["name"]}')
            delete_outcome_results(course['id'])
            print('old outcome results deleted')

            print(f'outcomes results to upload: {len(outcome_results)}')
            upsert_outcome_results(outcome_results)
            print('result upsert complete')

        # count = count + 1
        # if count > 5:
        #     break

def insert_grades(current_term=10):
    print(f'Grade pull started at {datetime.now()}')

    outcome_results = query_current_outcome_results(current_term)
    drop_eligible_results = outcome_results.loc[
        outcome_results['submitted_or_assessed_at'] < CUTOFF_DATE]

    # get min score from drop_eligible_results
    group_cols = ['links.user', 'course_id', 'outcome_id']
    min_score = drop_eligible_results.groupby(group_cols).agg(
        min_score=('score', 'min')).reset_index()
    full_avg = outcome_results.groupby(group_cols).agg(
        full_avg=('score', 'mean'),
        count=('score', 'count'),
        sum=('score', 'sum')).reset_index()
    outcome_avgs = pd.merge(min_score, full_avg, on=group_cols)
    outcome_avgs['drop_avg'] = (outcome_avgs['sum'] - outcome_avgs[
        'min_score']) / (outcome_avgs['count'] - 1)

    # Pick the higher average
    outcome_avgs['outcome_avg'] = np.where(
        outcome_avgs['drop_avg'] > outcome_avgs['full_avg'],
        outcome_avgs['drop_avg'], outcome_avgs['full_avg'])

    # calculate the grades
    group_cols = ['links.user', 'course_id']
    grades = outcome_avgs.groupby(group_cols).agg(
        grade_dict=('outcome_avg', calculate_traditional_grade))
    grades.reset_index(inplace=True)

    # format the grades
    grades[['threshold', 'min_score', 'grade']] = pd.DataFrame(
        grades['grade_dict'].values.tolist(), index=grades.index)

    # Make a new record
    print(f'Record created at {datetime.now()}')
    record_id = create_record(current_term)
    grades['record_id'] = record_id

    # Create grades_dict for database insert
    grades.rename(columns={'links.user': 'user_id'}, inplace=True)
    grade_cols = ['course_id', 'user_id', 'threshold', 'min_score', 'grade',
                  'record_id']
    grades_list = grades[grade_cols].to_dict('r')

    # Delete grades from current term
    delete_grades_current_term(current_term)

    # Insert into Database
    if len(grades_list):
        insert_grades_to_db(grades_list)


def calc_outcome_avgs(outcome_results):
    '''
    Calculates outcome averages with both simple and weighted averages,
    choosing the higher of the two
    :param outcome_results:
    :return: DataFrame of outcome_averages with max of two averages
    '''

    group_cols = ['links.user', 'outcome_id', 'course_id']

    # Calculate the average without dropping the low score
    no_drop_avg = outcome_results.groupby(group_cols).agg(
        no_drop_score=('score', 'mean')).reset_index()

    # Calculate the average without dropping the low score
    outcome_results_drop_min = outcome_results[outcome_results['rank'] != 1.0]
    drop_avg = outcome_results_drop_min.groupby(
        group_cols).agg(drop_score=('score', 'mean')).reset_index()

    # Merge them together
    outcome_averages = pd.merge(no_drop_avg, drop_avg, on=group_cols)

    # Pick the greater average and note if a score was dropped
    outcome_averages['outcome_avg'] = outcome_averages[
        ['no_drop_score', 'drop_score']].max(axis=1).round(2)
    outcome_averages['drop_min'] = np.where(
        outcome_averages['no_drop_score'] < outcome_averages['drop_score'],
        True, False)

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
    Cleans up formatting of outcome_results DataFrame
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


def update_course_students(current_term):
    # Query current courses
    courses = get_db_courses(current_term)
    pattern = '@dtech|Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'

    for course in courses:
        course_id = course[0]
        course_name = course[1]
        # Filter out non-academic courses
        if re.match(pattern, course_name):
            print(course_name)
            continue

        # Get course students
        students = get_course_users({'id': course_id})
        # Get user IDs in a list
        student_dicts = [{'course_id': course_id, 'user_id': student['id']} for
                         student in students]

        if student_dicts:
            # delete previous course roster
            delete_course_students(course['id'])
            # insert current roster
            insert_course_students(student_dicts)


def update_courses(current_term):
    courses = get_courses(current_term)
    upsert_courses(courses)


def update_users():
    '''
    Updates users table in database with all current account users
    :return: None
    '''
    users = get_users()
    upsert_users(users)


if __name__ == '__main__':
    start = time.time()
    # import os
    # print(os.getenv('PULL_CONFIG'))
    current_term = 11
    # update_users()
    # update_courses(current_term)
    # update_course_students(current_term)
    pull_outcome_results(current_term)
    insert_grades(current_term)

    end = time.time()
    print(f'pull took: {end - start} seconds')
